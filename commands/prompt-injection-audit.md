---
description: Audit an LLM-backed feature for prompt-injection exposure. Read-only, findings only.
argument-hint: "[file or directory to audit]"
---

Use the `prompt-injection-audit` skill to audit the target below.

**Target:** $ARGUMENTS

If the target is empty, find the LLM-backed code in the current working directory
and audit that, saying up front which files you picked and why.

Hold the skill's contract exactly, since these are the points an audit usually
drifts on:

- Read `references/checks.md` before grading anything.
- **Findings only.** Do not write fixes, refactor, or add defenses. If fixes are
  wanted, deliver the audit first and offer them as a separate step.
- **Every finding needs `file:line` evidence.** No evidence means it belongs on
  the could-not-verify list, not in the findings.
- **A prompt-level defense grades FAIL,** never partial credit.
- Grade as if the model is fully cooperating with the attacker. "The model
  wouldn't do that" is not a control.
- Produce the report in the exact shape from `references/report-format.md`,
  including the JSON block, then validate it with
  `scripts/validate_findings.py`.
- End with the could-not-verify list, naming the exact files or layers to share
  next.

If no model call is found in the target, say so and stop. There is nothing to
audit yet.
