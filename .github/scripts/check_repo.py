#!/usr/bin/env python3
"""Repo invariants for prompt-injection-audit. Run locally: python .github/scripts/check_repo.py

Guards the things that silently rot: the skill's frontmatter contract, the
plugin manifests, and the fact that every JSON example in the docs must
actually pass the validator it tells people to run.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILL = os.path.join(ROOT, "skills", "prompt-injection-audit")
VALIDATOR = os.path.join(SKILL, "scripts", "validate_findings.py")

failures = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not ok:
        failures.append(name)


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


# --- 1. SKILL.md frontmatter contract ---------------------------------------
raw = read("skills", "prompt-injection-audit", "SKILL.md")
fm = raw.split("---")[1]
name = re.search(r"^name:\s*(.+)$", fm, re.M).group(1).strip()
desc = re.search(r"^description:\s*(.+)$", fm, re.M).group(1).strip()

check("skill name is a valid slug", re.fullmatch(r"[a-z0-9-]{1,64}", name) is not None, name)
check("skill name matches its directory", name == os.path.basename(SKILL), name)
check("description within 1024 chars", len(desc) <= 1024, f"{len(desc)}/1024")
check("frontmatter has only name and description",
      set(re.findall(r"^(\w+):", fm, re.M)) == {"name", "description"})

# --- 2. Plugin manifests -----------------------------------------------------
plugin = json.loads(read(".claude-plugin", "plugin.json"))
market = json.loads(read(".claude-plugin", "marketplace.json"))
check("plugin.json name matches skill", plugin["name"] == name, plugin["name"])
check("marketplace lists the plugin",
      any(p["name"] == plugin["name"] for p in market["plugins"]))

# --- 3. Files SKILL.md points at actually exist ------------------------------
for ref in re.findall(r"`((?:references|scripts)/[\w.\-/]+)`", raw):
    check(f"SKILL.md reference exists: {ref}", os.path.isfile(os.path.join(SKILL, ref)))

# --- 4. Every JSON example in the docs passes the validator ------------------
for rel in ["README.md", "skills/prompt-injection-audit/references/report-format.md"]:
    for i, block in enumerate(re.findall(r"```json\n(.*?)```", read(rel), re.S)):
        try:
            json.loads(block)
        except json.JSONDecodeError as e:
            check(f"{rel} json[{i}] parses", False, str(e))
            continue
        proc = subprocess.run([sys.executable, VALIDATOR, "-"],
                              input=block, capture_output=True, text=True)
        check(f"{rel} json[{i}] passes validator",
              proc.returncode == 0, proc.stderr.strip()[:120])

# --- 5. Validator still enforces its load-bearing rule -----------------------
no_evidence = json.dumps({
    "audit": {"scope_reviewed": [], "model_calls": [], "stack_detected": "x", "clean": False},
    "findings": [{"id": "F1", "check": "S1", "check_name": "n", "title": "t",
                  "severity": "High", "status": "FAIL", "why_it_fails": "w",
                  "what_passing_looks_like": "p", "evidence": [], "owasp": ["LLM01"]}],
    "could_not_verify": [],
})
proc = subprocess.run([sys.executable, VALIDATOR, "-"],
                      input=no_evidence, capture_output=True, text=True)
check("validator rejects a FAIL finding with no evidence", proc.returncode == 1)

# --- 6. No em or en dashes ---------------------------------------------------
offenders = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__"}]
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        try:
            s = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        n = s.count("\u2014") + s.count("\u2013")
        if n:
            offenders.append(f"{os.path.relpath(p, ROOT)}({n})")
check("no em or en dashes", not offenders, " ".join(offenders[:5]))

# --- 7. Internal anchor links resolve ---------------------------------------
def slug(h):
    return re.sub(r"[^\w\s-]", "", h.strip().lower()).replace(" ", "-")

for rel in ["README.md", "skills/prompt-injection-audit/references/checks.md"]:
    txt = read(rel)
    heads = {slug(m) for m in re.findall(r"^#{1,6}\s+(.*)$", txt, re.M)}
    broken = [l for l in re.findall(r"\]\(#([^)]+)\)", txt) if l not in heads]
    check(f"{rel} anchors resolve", not broken, " ".join(broken[:3]))

print()
if failures:
    print(f"{len(failures)} check(s) failed")
    sys.exit(1)
print("all checks passed")
