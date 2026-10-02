import json, os, subprocess, sys, time, re
from pathlib import Path

PROJECT_PATH = "/scratch/k2983/root-project/pcb-schematic-gen/SchGen"
VENV_PYTHON = str(Path(PROJECT_PATH) / ".venv" / "bin" / "python3")

# v5: full, unbiased re-validation of the pin_number-preference fix
# (config.py NOTE 6 + symbol_context.py's new pin_number field, 2026-10-01)
# against ALL 129 currently Layer1-passing candidates, run fresh from
# scratch. This fix changes the system prompt for EVERY generation call
# (not just retries), so no old result is reusable - every candidate needs
# a fresh run, same discipline as the v4 diversity-fix validation.
RESULTS_IN = "/tmp/claude-997413182/-clusterhome-2983-code-schematic/070d7a28-c4cf-4ee6-a3f4-de8241396770/scratchpad/t013_full_layer1_twostage_v2_results.json"
RESULTS_OUT = str(Path(__file__).resolve().parent / "t013_full_schgen_v5_pinnum_results.json")

GPU_BUSY_THRESHOLD_MB = 300
POLL_INTERVAL_S = 30

def gpu_used_mb() -> int:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True, text=True,
    ).stdout.strip()
    return int(out.splitlines()[0])

def wait_for_gpu_headroom():
    waited = 0
    while True:
        used = gpu_used_mb()
        if used <= GPU_BUSY_THRESHOLD_MB:
            if waited > 0:
                print(f"  [gpu-wait] clear now ({used}MB used), proceeding after {waited}s waiting", flush=True)
            return
        print(f"  [gpu-wait] GPU busy ({used}MB used), waiting {POLL_INTERVAL_S}s...", flush=True)
        time.sleep(POLL_INTERVAL_S)
        waited += POLL_INTERVAL_S

with open(RESULTS_IN) as f:
    layer1_results = json.load(f)
passed = [r for r in layer1_results if r["status"] == "passed" and r.get("detailed_prompt")]

try:
    with open(RESULTS_OUT) as f:
        schgen_results = json.load(f)
except FileNotFoundError:
    schgen_results = []
done_ids = {e["part_id"] for e in schgen_results}
remaining = [r for r in passed if r["part_id"] not in done_ids]
print(f"{len(done_ids)} already done, {len(remaining)} remaining (of {len(passed)} Layer1-passing candidates)", flush=True)

def slugify(part_id: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", part_id).strip("_").lower()
    return f"t013v5pinnum_{s}"

env = os.environ.copy()
env["PROJECT_PATH"] = PROJECT_PATH

t_start = time.time()
for i, r in enumerate(remaining):
    part_id = r["part_id"]
    project_name = slugify(part_id)
    prompt = r["detailed_prompt"]

    print(f"--- [{len(done_ids)+i+1}/{len(passed)}] {part_id}: checking GPU headroom ---", flush=True)
    wait_for_gpu_headroom()

    t0 = time.time()
    cmd = [
        VENV_PYTHON, "schematic_generation/verify_and_retry.py",
        "--prompt", prompt,
        "--project_name", project_name,
        "--max_attempts", "3",
    ]
    proc = subprocess.run(cmd, cwd=PROJECT_PATH, env=env, text=True, capture_output=True)
    elapsed = time.time() - t0
    stdout = proc.stdout
    ok = "[PASS] Attempt" in stdout and proc.returncode == 0
    entry = {
        "idx": len(done_ids) + i, "part_id": part_id, "project_name": project_name,
        "returncode": proc.returncode, "erc_clean": ok, "elapsed_s": round(elapsed, 1),
        "fix": "pin_number_preference",
    }
    m = re.search(r"Attempt (\d+) succeeded", stdout)
    if m:
        entry["attempts_used"] = int(m.group(1))
    entry["stdout_tail"] = stdout[-2000:]
    if proc.stderr:
        entry["stderr_tail"] = proc.stderr[-1000:]
    schgen_results.append(entry)

    elapsed_total = time.time() - t_start
    print(f"[{len(done_ids)+i+1}/{len(passed)}] {part_id}: erc_clean={ok} "
          f"(attempts={entry.get('attempts_used','?')}, {elapsed:.0f}s, run total {elapsed_total/60:.1f}m)", flush=True)

    with open(RESULTS_OUT, "w") as f:
        json.dump(schgen_results, f, indent=2, default=str)

print()
print("=" * 70)
print(f"FINAL SUMMARY (full {len(passed)})")
n_ok = sum(1 for e in schgen_results if e["erc_clean"])
print(f"{n_ok}/{len(schgen_results)} reached 0 ERC errors")
total_time = sum(e["elapsed_s"] for e in schgen_results)
print(f"Total time: {total_time/60:.1f} minutes")
