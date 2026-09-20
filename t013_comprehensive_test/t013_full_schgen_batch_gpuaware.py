import json, os, subprocess, sys, time, re
from pathlib import Path

PROJECT_PATH = "/scratch/k2983/root-project/pcb-schematic-gen/SchGen"
_HERE = Path(__file__).resolve().parent
RESULTS_IN = str(_HERE / "t013_full_layer1_results.json")
RESULTS_OUT = str(_HERE / "t013_full_schgen_results.json")

# Our own process alone peaks near ~31GB of the 32.6GB card (confirmed via
# live nvidia-smi trace). Tried raising this to 2000 on 2026-09-20 to test
# whether k465's steady ~1.1GB baseline could be tolerated - it could not:
# the load was actually attempted (not just idle-polled) and still got
# killed, confirming this is a real capacity conflict, not a false-positive
# kill. Back to requiring the GPU to be genuinely free before attempting.
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

with open(RESULTS_OUT) as f:
    schgen_results = json.load(f)
done_ids = {e["part_id"] for e in schgen_results}
remaining = [r for r in passed if r["part_id"] not in done_ids]
print(f"{len(done_ids)} already done, {len(remaining)} remaining", flush=True)

def slugify(part_id: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", part_id).strip("_").lower()
    return f"t013_{s}"

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
        sys.executable, "schematic_generation/verify_and_retry.py",
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
print("FINAL SUMMARY (full 103)")
n_ok = sum(1 for e in schgen_results if e["erc_clean"])
print(f"{n_ok}/{len(schgen_results)} reached 0 ERC errors")
