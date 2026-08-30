#!/usr/bin/env python3
"""
Validate a prompt-injection-audit findings JSON against the fixed contract.

Usage:
    python scripts/validate_findings.py findings.json
    some_command | python scripts/validate_findings.py -      # read stdin

Exit code 0 = valid, 1 = invalid (errors printed to stderr).

This script is the executable definition of the output schema described in
references/report-format.md. It checks structure and the invariants that are easy
to get wrong under pressure. It does NOT judge whether the findings are correct.
The load-bearing rule it enforces: every FAIL finding must carry file:line
evidence. A finding with no evidence is not a finding; it belongs in
could_not_verify.
"""
import json
import sys

CHECKS = {"S1", "S2", "S3", "G1", "G2", "G3", "G4", "G5"}
SEVERITIES = {"Critical", "High", "Medium", "Low"}
STATUSES = {"FAIL", "PASS"}
OWASP_IDS = {f"LLM{n:02d}" for n in range(1, 11)}


def err(errors, msg):
    errors.append(msg)


def validate(doc):
    errors = []

    if not isinstance(doc, dict):
        return ["top level must be a JSON object"]

    # --- audit block ---
    audit = doc.get("audit")
    if not isinstance(audit, dict):
        err(errors, "missing or non-object 'audit' block")
        audit = {}
    else:
        if not isinstance(audit.get("scope_reviewed"), list):
            err(errors, "audit.scope_reviewed must be a list of paths")
        if not isinstance(audit.get("model_calls"), list):
            err(errors, "audit.model_calls must be a list (may be empty if none found)")
        if not isinstance(audit.get("stack_detected"), str):
            err(errors, "audit.stack_detected must be a string")
        if not isinstance(audit.get("clean"), bool):
            err(errors, "audit.clean must be a boolean")

    # --- findings ---
    findings = doc.get("findings")
    if not isinstance(findings, list):
        err(errors, "'findings' must be a list")
        findings = []

    seen_ids = set()
    for i, f in enumerate(findings):
        where = f"findings[{i}]"
        if not isinstance(f, dict):
            err(errors, f"{where} must be an object")
            continue

        fid = f.get("id")
        if not isinstance(fid, str) or not fid:
            err(errors, f"{where}.id must be a non-empty string")
        elif fid in seen_ids:
            err(errors, f"{where}.id '{fid}' is duplicated")
        else:
            seen_ids.add(fid)

        if f.get("check") not in CHECKS:
            err(errors, f"{where}.check must be one of {sorted(CHECKS)}")
        if not isinstance(f.get("check_name"), str) or not f.get("check_name"):
            err(errors, f"{where}.check_name must be a non-empty string")
        if not isinstance(f.get("title"), str) or not f.get("title"):
            err(errors, f"{where}.title must be a non-empty string")
        if f.get("severity") not in SEVERITIES:
            err(errors, f"{where}.severity must be one of {sorted(SEVERITIES)}")

        status = f.get("status")
        if status not in STATUSES:
            err(errors, f"{where}.status must be one of {sorted(STATUSES)}")

        for field in ("why_it_fails", "what_passing_looks_like"):
            if not isinstance(f.get(field), str) or not f.get(field):
                err(errors, f"{where}.{field} must be a non-empty string")

        # Evidence: required and non-empty for FAIL findings. This is the core rule.
        evidence = f.get("evidence")
        if not isinstance(evidence, list):
            err(errors, f"{where}.evidence must be a list")
            evidence = []
        if status == "FAIL" and len(evidence) == 0:
            err(
                errors,
                f"{where} is FAIL but has no evidence. A finding without file:line "
                f"evidence is not a finding; move it to could_not_verify",
            )
        for j, ev in enumerate(evidence):
            ew = f"{where}.evidence[{j}]"
            if not isinstance(ev, dict):
                err(errors, f"{ew} must be an object")
                continue
            if not isinstance(ev.get("file"), str) or not ev.get("file"):
                err(errors, f"{ew}.file must be a non-empty string")
            if not isinstance(ev.get("line"), int):
                err(errors, f"{ew}.line must be an integer")

        owasp = f.get("owasp")
        if not isinstance(owasp, list):
            err(errors, f"{where}.owasp must be a list of OWASP LLM IDs (may be empty for G5)")
        else:
            for oid in owasp:
                if oid not in OWASP_IDS:
                    err(errors, f"{where}.owasp contains invalid id '{oid}' (expected LLM01 to LLM10)")
            if not owasp and f.get("check") != "G5":
                err(errors, f"{where}.owasp is empty but only G5 may omit an OWASP mapping")

        if "prompt_level_defense_present" in f and not isinstance(
            f["prompt_level_defense_present"], bool
        ):
            err(errors, f"{where}.prompt_level_defense_present must be a boolean")

    # --- clean/findings consistency ---
    clean = audit.get("clean")
    if clean is True and len(findings) > 0:
        err(errors, "audit.clean is true but findings is non-empty")
    if clean is False and len(findings) == 0:
        err(
            errors,
            "audit.clean is false but findings is empty. Set clean=true and use the "
            "clean-report sentence, or add the findings",
        )

    # --- could_not_verify ---
    cnv = doc.get("could_not_verify")
    if not isinstance(cnv, list):
        err(errors, "'could_not_verify' must be a list (use [] only if you truly saw the whole system)")
    else:
        for i, item in enumerate(cnv):
            if not isinstance(item, dict):
                err(errors, f"could_not_verify[{i}] must be an object")
                continue
            for field in ("concern", "missing", "to_verify_share"):
                if not isinstance(item.get(field), str) or not item.get(field):
                    err(errors, f"could_not_verify[{i}].{field} must be a non-empty string")

    # --- adjacent_out_of_scope (optional) ---
    adj = doc.get("adjacent_out_of_scope", [])
    if not isinstance(adj, list):
        err(errors, "'adjacent_out_of_scope' must be a list if present")

    # --- notes ---
    if not isinstance(doc.get("notes", []), list):
        err(errors, "'notes' must be a list if present")

    return errors


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)

    raw = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1], encoding="utf-8").read()
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"INVALID: not parseable JSON. {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate(doc)
    if errors:
        print(f"INVALID: {len(errors)} problem(s)", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    n = len(doc.get("findings", []))
    clean = doc.get("audit", {}).get("clean")
    print(f"VALID: {n} finding(s), clean={clean}")
    sys.exit(0)


if __name__ == "__main__":
    main()
