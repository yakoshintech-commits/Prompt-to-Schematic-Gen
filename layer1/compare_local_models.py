"""
Compare llama3.1:8b (the task spec's default) against deepseek-coder:33b
(already pulled for this portfolio's "code execution" role, per
context.md's Model Assignment) on this exact structured-JSON-with-strict-
vocabulary task, per T001 Step 2's instruction not to just default without
testing. Real output, not a synthetic guess at which would perform better.
"""

import json
import subprocess
import sys
import time

import requests

sys.path.insert(0, "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")
from kg_open_schematics_store import OpenSchematicsKGStore
from prompts import build_system_prompt, build_user_prompt

kg = OpenSchematicsKGStore(base_dir="/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")
allowed = [kg.get_component("R"), kg.get_component("LED")]
allowed_json = json.dumps(allowed, indent=2)

vague_prompt = "blink an LED with a current-limiting resistor"
system_prompt = build_system_prompt(allowed_json)
user_prompt = build_user_prompt(vague_prompt)


def check_gpu_headroom_gb():
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
        capture_output=True, text=True,
    )
    used, total = (int(x.strip()) for x in result.stdout.strip().split(","))
    return (total - used) / 1024


def call_model(model_name: str) -> dict:
    headroom = check_gpu_headroom_gb()
    print(f"[{model_name}] GPU headroom before call: {headroom:.1f} GB")
    if headroom < 3.0:
        raise RuntimeError(f"Refusing to run {model_name}: only {headroom:.1f} GB free, need several GB margin.")

    start = time.time()
    resp = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0},
        },
        timeout=180,
    )
    elapsed = time.time() - start
    resp.raise_for_status()
    raw = resp.json()["message"]["content"]
    return {"model": model_name, "elapsed_s": elapsed, "raw": raw}


def evaluate(raw: str, allowed_ids: set, allowed_pins: dict) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        return {"valid_json": False, "error": str(e)}

    hallucinations = []
    for comp in obj.get("components", []):
        pid = comp.get("part_id")
        if pid not in allowed_ids:
            hallucinations.append(f"invented part_id {pid!r}")
    for net in obj.get("nets", []):
        for ep in net.get("endpoints", []):
            ref = ep.get("ref")
            comp_pid = next((c.get("part_id") for c in obj.get("components", []) if c.get("ref") == ref), None)
            real_pins = allowed_pins.get(comp_pid, set())
            pin_key = (str(ep.get("pin_id")), str(ep.get("pin_name")))
            if pin_key not in real_pins:
                hallucinations.append(f"invented pin {pin_key} on {ref} ({comp_pid})")

    return {
        "valid_json": True,
        "has_required_keys": all(k in obj for k in ("id", "name", "summary", "components", "nets")),
        "n_components": len(obj.get("components", [])),
        "n_nets": len(obj.get("nets", [])),
        "hallucinations": hallucinations,
        "parsed": obj,
    }


allowed_ids = {c["id"] for c in allowed}
allowed_pins = {
    c["id"]: {(str(p["num"]), str(p["name"])) for p in c["pins"]}
    for c in allowed
}

for model in ["llama3.1:8b", "deepseek-coder:33b"]:
    print(f"\n{'='*20} {model} {'='*20}")
    result = call_model(model)
    print(f"elapsed: {result['elapsed_s']:.1f}s")
    print("raw output:\n", result["raw"][:1500])
    evaluation = evaluate(result["raw"], allowed_ids, allowed_pins)
    print("\nevaluation:", json.dumps({k: v for k, v in evaluation.items() if k != "parsed"}, indent=2))
