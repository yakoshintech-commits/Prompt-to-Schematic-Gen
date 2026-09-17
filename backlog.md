# Product Backlog

| ID | Title | Status | Assigned | Notes |
|---|---|---|---|---|
| T001 | Build Layer 1 grounded architecture-candidate pipeline, with skills setup | ready | Claude Code | See tasks/T001-layer1-grounded-pipeline.md |
| T002 | Migrate SchGen's fine-tuned model (gpt-oss-20b + LoRA adapter) to Ollama-served GGUF weights | backlog | unassigned | Sponsor goal: unify all local model serving onto Ollama. Feasibility unproven - gpt-oss-20b's MoE/MXFP4 architecture may lack clean llama.cpp/GGUF conversion support. Investigate feasibility before committing to a full Work Item spec. Sequenced after current SchGen generalization testing. |
