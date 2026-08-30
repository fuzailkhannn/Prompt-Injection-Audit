# Security Policy

## Reporting a vulnerability

Please report security issues privately through
[GitHub Security Advisories](https://github.com/fuzailkhannn/Prompt-Injection-Audit/security/advisories/new)
rather than opening a public issue.

Expect an initial response within 7 days.

## What is in scope

This repository is a Claude Skill: Markdown instructions plus one dependency-free
Python validator. It does not run as a service and holds no credentials, so the
interesting failures are about the audit being *wrong* rather than the code being
exploited. In scope:

- **A false all-clear.** A pattern of vulnerable code the skill reports as clean,
  especially one where a real control is missing but the skill credits a
  prompt-level defense as if it were a control.
- **Validator bypass.** A findings JSON that `scripts/validate_findings.py` accepts
  despite breaking the contract, above all a `FAIL` finding with no `file:line`
  evidence.
- **Injection into the audit itself.** Code or comments crafted so that a model
  reading them follows them as instructions and suppresses or fabricates findings.
- Anything in this repository that could harm someone who installs the skill.

## What is not in scope

- The deliberately vulnerable samples in [`fixtures/`](fixtures/). Every one of them
  is insecure on purpose, and the credentials there are placeholders. See
  [`fixtures/EXPECTED.md`](fixtures/EXPECTED.md).
- Prompt injection against Claude generally, rather than against this skill.
- The skill missing a vulnerability class it never claimed to cover. Read
  [What it does NOT catch](README.md#what-it-does-not-catch) first.

## A word on what this tool is

This skill is a static reading of code by a language model. It does not run your
application, send payloads, or prove exploitability. A clean report means "no
findings in the code I could review," never "this code is secure." Treat it as a
focused first pass, and pair it with review by a security-minded person before you
trust an AI feature with other people's data.
