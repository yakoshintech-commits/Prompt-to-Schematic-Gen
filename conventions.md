# Engineering Standards - v1

Cross-project rules, such as commit message format, the development-cost bias correction, and the tool-interface preference, live in global.md at the portfolio root and are not duplicated here.

## Definition of Done, project-specific

- The Work Item's named verification command passes, with real captured output in evidence/.
- handoff.md is updated, with the Evidence field pointing at that real, already-existing file.
- Work is committed, with scope respected.
- No forbidden path, listed below, was touched.
- Any non-obvious finding about PCBSchemaGen_v2 or SchGen internals is written into the relevant skills/ file, not left only in the session transcript.

## Forbidden paths

- Any file inside the external SchGen repository checkout. Read-only dependency, never run or modified by this project's own Work Items.
- Any file inside the external PCBSchemaGen_v2 repository checkout, except adding a new, clearly named wrapper module under this project's own layer1/ directory that imports from it read-only.
- global.md, instructions.md, conventions.md, and skills/manifest.yaml. These require an explicit Sponsor-directed Change Control entry, per PIPELINE.md section 16, not an in-sprint edit by the Developer.

## Rollback

The portfolio default applies unchanged. Tag before each sprint. On failure, git reset --hard sprint-start-<id>.

## Domain terminology

- KG, knowledge graph: PCBSchemaGen_v2's component, pin, and constraint data. Either the default 48-component set, or the 241-component Open-Schematics set loaded through this project's OpenSchematicsKGStore wrapper.
- Candidate: one proposed circuit architecture produced by Layer 1's generator, with components, nets, and a verification_status.
- Snapshot: the components-plus-nets data structure that PCBSchemaGen_v2's verifier functions consume.
- verification_status: one of passed, failed_checks, or rejected. Rejected means a hallucinated part or pin was found, caught before the real verifier even ran.

## Review Cadence Policy

The portfolio default applies unchanged. See PIPELINE.md section 12.

## Current university compute window

Ten-day access per allocation cycle. Treat all university-local storage as ephemeral. See config/paths.md for the durable dataset location and for the session start and end sync commands.
