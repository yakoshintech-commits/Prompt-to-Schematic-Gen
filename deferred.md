# Deferred Register

| Artifact | Trigger | Status | Last checked | Evidence |
|---|---|---|---|---|
| review_check.py | Caught "said X, didn't do X" 3x | armed | setup | 0 / 3 |
| reviewer.md + review_log.md | 5 sprints shipped, or a repeated mistake | armed | setup | 0 / 5 sprints |
| sync.py | Generated index drifts once | armed | setup | 0 |
| health_score.py | Review skipped or tightened 5+ times | armed | setup | 0 |
| Model scorecard | 10+ sprints in sessions.md | armed | setup | 0 / 10 sprints |
| Parallel execution via worktrees | Serial is the observed bottleneck | armed | setup | no |
| Cost tracking / capacity planning | Cost per sprint visible and you need to plan | armed | setup | 0 |
| global.md hash propagation automation | global.md edited and 3+ projects are active | armed | setup | 0 |
| sessions.md log rotation | sessions.md exceeds 200 rows | armed | setup | 0 |
| Evidence directory rotation | evidence/ grows large enough to noticeably slow git operations or clones | armed | setup | 0 |
| Git hook binding for worktrees | Parallel worktree sessions are actually in use and a hook is observed not firing in one | armed | setup | 0 |
| Lesson conflict resolution rule | Two projects record contradictory lessons and one is proposed for promotion to global.md | armed | setup | 0 |
| Batched Trigger Review scheduling across projects | 5+ projects are active and ad hoc review timing is observed to cause context-switching fatigue or missed reviews | armed | setup | 0 |
| Adversarial review in a fresh context window | The Scanner and QA Lead both exist and are reliable, and single-pass QA review is missing issues | armed | setup | 0 |
| Auto-PR / babysit-to-merge automation | Adversarial review exists and is trusted, and you want to remove the Sponsor from the loop on low-risk changes specifically | armed | setup | 0 |
| Unattended long-running sessions | Adversarial review and auto-PR above both exist and are trusted | armed | setup | 0 |
| Remove kicad_add_symbol.py fuzzy-match auto-correction stopgap | Layer 1's validate_facts.py hard hallucination filter is built and catches unresolvable component names before generation reaches SchGen | shelved | 2026-09-18 | Built 2026-09-18 after verify-and-retry failed 3/3 attempts to self-correct an exact-string near-miss even with correct feedback delivered in proper multi-turn structure - then reverted same day (Sponsor decision) so this hallucination class gets the same systemic Layer 1 fix as the others found alongside it, instead of a special case for whichever one got fixed first. See context.md Lessons v3 and backlog.md T001 findings row. |

Statuses: armed, fired, building, built, shelved.

Two rules. A fired row must become a Work Item in the same session it fires. A row is never deleted, only marked shelved with a note if the artifact turns out not to be needed.

See PIPELINE.md section 11.1 for the Trigger Review ritual, and section 12 for the adaptive cadence that governs how often this gets checked.
