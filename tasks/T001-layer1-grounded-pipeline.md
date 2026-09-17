# T001 - Layer 1 grounded architecture-candidate pipeline, with skills setup

## Inputs

- PCBSchemaGen_v2 checkout, at the path named pcbschemagen_dir in config/paths.md. Read-only, except for one additive wrapper described below.
- SchGen checkout, at the path named schgen_dir in config/paths.md. Read-only. Not run, not called, not touched by this Work Item.
- This project's empty skills/ directory. Populated as part of this Work Item, not before it.

## Outputs

- skills/pcbschemagen-verifier/SKILL.md
- skills/schgen-integration/SKILL.md
- skills/layer1-pipeline/SKILL.md
- skills/local-llm-setup/SKILL.md
- layer1/kg_open_schematics_store.py, plus its test
- layer1/retrieval.py, plus its test
- layer1/prompts.py
- layer1/generate_candidates.py
- layer1/validate_facts.py, plus its test
- layer1/verify_candidate.py, plus its test
- layer1/pipeline.py
- layer1/test_pipeline.py

## Acceptance criteria

- Layer 1 runs end-to-end on three or more vague prompts spanning different circuit domains and returns ranked, verified candidates for each.
- Every candidate's verification_status is one of passed, failed_checks, or rejected, set correctly according to real, not simulated, checks.
- No hallucinated part_id or pin_id/pin_name reaches a candidate without being caught, either by the deterministic filter or by the real verifier.
- Every step below that involves genuine investigation, meaning running code or reading source to confirm a real behavior rather than assuming it, ends with that finding written into the relevant skills/ file, in addition to being shown in the session.
- SchGen is never run, called, or interrupted by any part of this Work Item.
- Before any local model inference runs on GPU, available VRAM headroom is checked and confirmed sufficient beyond whatever else is already using the GPU. Default to CPU-only inference if this cannot be confirmed.

## Verification command

```
python layer1/test_pipeline.py 2>&1 | tee evidence/T001-<sprint-id>.log
```

## Scope

- May create or edit anything under layer1/ and skills/ in this project.
- May not edit anything inside schgen_dir or pcbschemagen_dir, except adding new files under this project's own layer1/ directory that import from pcbschemagen_dir read-only.
- May not run, call, or otherwise interact with SchGen itself.

## SOPs referenced

None yet. This Work Item is itself the source of the first candidate SOPs. Once a pattern from it looks reusable across future Work Items, propose it into skills/candidates/ and vet it per PIPELINE.md section 9.2, rather than writing it directly into skills/manifest.yaml now.

---

## Detailed steps

### Step 0: skills directory and KGStore investigation

1. Create the skills/ structure listed under Outputs, with placeholder SKILL.md files. Each SKILL.md should have a Purpose section, a Key facts section with empirically confirmed facts only, a Common mistakes to avoid section, and a Code references section.
2. Clone PCBSchemaGen_v2 if not already present at pcbschemagen_dir.
3. Install its dependencies, networkx and pyyaml.
4. Confirm by reading actual source, not by guessing: KGStore's full public interface in framework/topo/kg_loader.py, including method names, signatures, and return shapes. Confirm the real snapshot shape and call chain that validate_complex_task, augment_snapshot, and check_system_topology actually expect, by running a minimal test rather than trusting the README's inline pseudocode at face value if it disagrees with the code. Confirm whether augment_snapshot and anything else needed is re-exported from framework/topo/__init__.py or needs a direct submodule import. Confirm the full pin-role vocabulary and the four constraint predicate types, must_be_connected, supply_pair, differential_pair_must_be_distinct, and driving_pair, with their exact field shapes.
5. Write everything confirmed in step 4 into skills/pcbschemagen-verifier/SKILL.md before proceeding.

### Step 0b: the 241-component KG store

1. Confirm KGStore is hardcoded to component.json plus kg_component.json, the 48-component set, with no path override, and that kg/kg_open_schematics.json, the 241-component set, is not wired in by default.
2. Build layer1/kg_open_schematics_store.py: an OpenSchematicsKGStore class that mirrors KGStore's exact public interface but loads from the single merged 241-component file. Do not modify PCBSchemaGen_v2's own code.
3. Test it side by side against KGStore on a component that exists in both sets and one that only exists in the 241-set, to prove genuine wider coverage rather than a silent fallback. Show real output.
4. Confirm no part of framework/topo/ type-checks against KGStore specifically, meaning it is safe as a duck-typed drop-in. Grep for isinstance calls involving kg_store and report what is found.
5. Add this to skills/pcbschemagen-verifier/SKILL.md as its own section, "Using the 241-component KG instead of the default 48."

### Step 1: component retrieval module

Build layer1/retrieval.py with a function that does a cheap keyword-overlap ranking over the kg_store's components, matching against id, category, subcategory, and note fields, returning the top-k most relevant real components with their full pin list and constraints intact. Keep this simple for a first version. Leave a TODO comment noting embedding-based retrieval as a future improvement, rather than building it now. Test against three or four varied vague prompts and print the top-5 retrieved ids per prompt. If a real relevance gap turns up, meaning a genuinely matching component scores lower than an irrelevant one due to shallow keyword overlap, record it as a known limitation in skills/layer1-pipeline/SKILL.md.

### Step 2: constrained candidate generator

Build layer1/generate_candidates.py and layer1/prompts.py, keeping prompt text separate from logic. The generator retrieves the allowed component vocabulary, then sends one LLM call whose system prompt provides the retrieved components' full JSON as the only allowed vocabulary, and explicitly forbids inventing any part_id, pin_id, or pin_name not present verbatim in that data. Candidate schema: id, name, summary, tradeoffs, assumptions, components as a list of ref and part_id pairs, and nets as a list of name and endpoints, where each endpoint is ref, pin_id, and pin_name. Strict JSON output only. Parse defensively, stripping code fences if present, and surface parse errors clearly rather than failing silently.

Use a local model through Ollama for this call, not a paid API, per the project's constraints. Default to llama3.1:8b unless testing shows a different local model performs better on this specific structured-JSON task. Confirm the exact local API call shape and write it into skills/local-llm-setup/SKILL.md, including which model, why, the measured VRAM footprint, and the exact pull and call pattern used.

GPU safety is non-negotiable here. SchGen may be running concurrently in a separate process or environment. Do not assume the GPU is free. Before running any local model inference, check nvidia-smi and confirm there is enough free VRAM headroom beyond what is already in use, leaving several gigabytes of margin, not just the bare minimum. If in doubt, default to CPU-only inference rather than risk contending for GPU memory. Record whatever is confirmed or decided into skills/schgen-integration/SKILL.md under a "Coexisting safely with SchGen" section.

### Step 3: hard hallucination filter

Build layer1/validate_facts.py with a function that checks every part_id referenced in a candidate exists in kg_store, and every pin_id or pin_name referenced in its nets exists on that specific component's real pin list, returning a clear reason on the first mismatch found. This must run before the real verifier step, rejecting or flagging a failing candidate without wasting a verifier call on it. Test against hand-built synthetic candidates: one fully grounded, one with a hallucinated part_id, one with a hallucinated pin. Confirm both failure modes are caught, with real output shown.

### Step 4: wire in the real verifier

Build layer1/verify_candidate.py. A build_snapshot function converts a candidate's components and nets into the exact snapshot shape the verifier expects, per the real, empirically confirmed contract from Step 0, not by re-deriving from scratch or trusting the README's pseudocode literally. A verify_candidate function runs validate_parts_exist first, exiting early to a rejected status on failure, otherwise builds the snapshot and runs the real verifier chain, setting verification_status to passed or failed_checks and storing human-readable errors and warnings. Test against three synthetic candidates: one with a hallucinated part, expected to be rejected without calling the real verifier; one real but incompletely wired component, expected to trip a real constraint check; one fully correct, expected to pass. Show real verifier output for each.

### Step 5: orchestration and scoring

Build layer1/pipeline.py with a function that calls generate_candidates, runs verify_candidate on every result, and computes a deterministic weighted score per candidate from a weights dictionary, for example cost, simplicity, and part_availability. Part_availability is 1.0 if verification passed, else 0.0. Simplicity is an inverse function of component count. Cost is a placeholder value for all candidates for now, with a TODO noting a future real bill-of-materials cost lookup. Returns both the full candidate list and a ranked list, with verification-passed candidates always ranked above failed or rejected ones regardless of score. Does not auto-pick a winner. Write this pipeline's overall shape into skills/layer1-pipeline/SKILL.md once built.

### Step 6: end-to-end test

Write layer1/test_pipeline.py as a plain script. Run the full pipeline on at least three vague prompts spanning different circuit domains that plausibly match real components in the 241-component KG. Print, per prompt, each candidate's name, summary, verification_status, and any errors. Flag clearly if any candidate across all test runs has verification_status equal to rejected, since that means a hallucination slipped past the prompt-level constraints and was only caught by the deterministic filter, which is the single most important signal to surface. Record the final test results summary into skills/layer1-pipeline/SKILL.md as a dated "Last known test results" section.
