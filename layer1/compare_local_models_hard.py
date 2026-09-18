"""
Harder comparison: ask for something the allowed vocabulary (R, LED only)
cannot fully satisfy (a voltage regulator), testing Rule 3 compliance -
does the model correctly decline/flag the gap in "assumptions" rather than
inventing a part_id not present in the vocabulary?
"""

import json
import sys
import time

import requests

sys.path.insert(0, "/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")
from kg_open_schematics_store import OpenSchematicsKGStore
from prompts import build_system_prompt, build_user_prompt

kg = OpenSchematicsKGStore(base_dir="/scratch/k2983/root-project/pcb-schematic-gen/PCBSchemaGen_v2")
allowed = [kg.get_component("R"), kg.get_component("LED")]
allowed_json = json.dumps(allowed, indent=2)
allowed_ids = {c["id"] for c in allowed}

system_prompt = build_system_prompt(allowed_json)
user_prompt = build_user_prompt("regulate 12V down to 3.3V for a sensor board")


def call_model(model_name: str) -> str:
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
    print(f"[{model_name}] elapsed={elapsed:.1f}s")
    return raw


def check(raw: str):
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        print("INVALID JSON:", e)
        print(raw[:800])
        return
    invented = [c["part_id"] for c in obj.get("components", []) if c["part_id"] not in allowed_ids]
    print("components used:", [c["part_id"] for c in obj.get("components", [])])
    print("INVENTED part_ids not in vocabulary:", invented if invented else "none - correctly stayed within vocabulary")
    print("assumptions field:", obj.get("assumptions"))


for model in ["llama3.1:8b", "deepseek-coder:33b"]:
    print(f"\n{'='*20} {model} {'='*20}")
    raw = call_model(model)
    print("raw:\n", raw[:1000])
    print()
    check(raw)
