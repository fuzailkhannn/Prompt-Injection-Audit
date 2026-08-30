# Fixtures — expected results

This is the answer key for the fixtures. It is deliberately kept **out of the
fixture source files** so that running the audit against a fixture measures whether
the skill can *analyze the code*, not whether it can read an answer written in a
comment. When you test the skill yourself, point it at a fixture file and compare
its report to the row below.

"Min bar" = the findings a correct audit must produce. A report may also surface the
lower-severity extras noted; that's fine. For the secured fixtures, the bar is the
opposite: the listed axes **must not** be reported as findings.

Severities are the expected ballpark, not exact strings — Critical/High for
load-bearing breaches, Medium for disclosure, Low for enabling weaknesses.

---

## Vulnerable

### `fastapi_support_chatbot.py`
- **S1 (Critical)** — `customer_id` read from request body, not the session; any caller can name any customer.
- **S2 query (Critical)** — `SELECT … FROM customers` with no `WHERE`; the model is handed every customer.
- **Prompt-level defense (FAIL)** — the "never reveal / never show other customers" system prompt is the only thing standing in for a real boundary; graded FAIL, severity inherits (High).
- Extras allowed: S3 raw output pass-through (Medium); G5 no logging (Low); adjacent — hardcoded DB creds / `app_admin` role in source.

### `express_account_assistant.js`
- **Prompt-level defense (FAIL)** — the system prompt ("only reveal the current user's info", "refuse malicious requests") is the sole control; FAIL.
- **S1 (Critical)** — `userId` from `req.body`; the `WHERE id = $1` is keyed on an attacker-controlled id, so there is no identity boundary.
- Extras allowed: S3 raw output (Medium); G5 no logging (Low). Ordinary DB credential — **not** a credential finding.

### `nextjs_chat_route.ts`
- **S3 (Medium)** — the raw completion is streamed straight to the browser.
- **G4 (Medium)** — the catch block returns `err.message` **and** `err.stack` to the client.
- **Must NOT flag S1/S2 as findings** — identity comes from `getServerSession()` and the query is scoped by `account_id = session.user.id`. (A minor note that the `?? ""` fallback lacks an explicit auth rejection is acceptable; a cross-user finding is not.)

### `django_doc_qa.py`
- **S2 / retrieval scope (High–Critical)** — `Document.objects.get(id=doc_id)` has no `owner` filter; any user can load any document by id.
- **G2 (High)** — `document.body` is concatenated raw into the prompt; retrieved content is an injection channel, and here it's cross-user.
- Extras allowed: S1 — no auth decorator (only `@csrf_exempt`), so the endpoint is unauthenticated; adjacent — CSRF disabled.

### `fastapi_order_agent.py`
- **G1 (Critical)** — `cancel_order` and `issue_refund` execute with model-supplied `order_id` and no ownership check. Note the tell: `get_current_user` is injected as `user` but never used to authorize the action. Destructive/financial ⇒ top severity.

### `express_helpdesk.js`
- **G3 (High)** — user-authored ticket bodies are stored (`POST /tickets`), then **all** of today's tickets are loaded into the staff digest prompt (`GET /tickets/digest`); an injected ticket body executes in the elevated staff context later. A correct finding must cite **both** ends (store + later read-into-prompt). The digest being staff-only is not a defense — staff may read tickets, but the model acts on their content.

### `nextjs_supabase_chat.ts`
- **S2 credential (High)** — the client is built with `SUPABASE_SERVICE_ROLE_KEY`, which bypasses RLS. The `.eq("owner_id", session.user.id)` filter *looks* scoped, but the credential is elevated, so app-code filtering is the only control. This is the load-bearing finding and the key test of the credential-vs-query distinction.
- **Must NOT flag S1** — identity is from `getServerSession()` with an explicit 401.
- Extra allowed: S3 raw output (the `parsed` variable is actually the raw string) — Medium.

### `go_assistant.go` (unfamiliar-stack / graceful-degradation test)
- **S1 (Critical)** — `user_id` comes from a query param and is then discarded (`_ = userID`); no auth, no boundary.
- **S2 query (Critical)** — `SELECT … FROM billing` with no `WHERE`; all billing rows go to the model.
- **S3 (Medium)** — the raw answer is returned.
- The point of this one: the skill likely doesn't know `go-openai` idioms. A good report still traces query-param → unfiltered SQL → raw output, flags S1/S2 at minimum, and **names in its notes** that the stack was unfamiliar and it audited by data flow. Hedging a detail to could-not-verify is fine; missing the obvious data-flow breach is not.

---

## Secured (must report **no findings** on the listed axes)

Each of these contains a surface pattern a greedy auditor over-flags — a service-role
key name, a system prompt, a raw-looking try/catch, retrieved content — but is correct
underneath. Flagging any of the listed axes as a finding is a false positive.

### `fastapi_support_chatbot_secure.py`
- **No findings.** S1 via `Depends(get_current_user)`; query scoped by `Customer.id == user.id`; ordinary app session (not elevated); output whitelisted to `answer`; errors generic + logged; logging present.
- Legitimate **could-not-verify**: `get_current_user` / `get_session` internals are imported, not shown — noting "assumes the auth dependency verifies the session" is correct and is *not* a finding. A defense-in-depth note about RLS is acceptable but must not appear as a finding.

### `nextjs_supabase_chat_secure.ts`
- **No findings.** Anon key + RLS enforced at the database; identity from session with 401; output parsed and whitelisted to `reply`.
- Legitimate **could-not-verify**: the RLS policies themselves aren't in the file — "effectiveness depends on RLS policies on `projects`, which aren't shown; verify they exist" is the correct, honest note. It is *not* a finding. Flagging the anon-key client as a credential problem is a false positive — it's the correct counterpart to the service-role fixture.

### `express_account_assistant_secure.js`
- **No findings.** `requireAuth` sets `req.user`; query scoped to `req.user.id`; output whitelisted to `answer`; the catch returns a generic message + trace id and logs details server-side; logging present.
- The try/catch is the defensive-looking pattern that must **not** be flagged as G4. Legitimate could-not-verify: `requireAuth` internals not shown.

### `django_doc_qa_secure.py`
- **No findings.** `@login_required`; retrieval scoped by `owner=request.user` (so there is no cross-user content to inject — this is the load-bearing reason G2 does not apply); untrusted content is delimited (defense-in-depth); output whitelisted to `answer`.
- The `<DOCUMENT>` delimiting should be recognized as defense-in-depth, **not** as "the control" and not as a finding. The load-bearing fact is scoped retrieval. Flagging G2 here is a false positive.

---

## Coverage map

| Check | Vulnerable fixture(s) | Secured (must-not-flag) |
|-------|------------------------|--------------------------|
| S1 Identity boundary | 1, 2, 4, 8 | 9, 10, 11 |
| S2 query scope | 1, 4, 8 | 9, 11 |
| S2 credential scope | 7 | 10 (anon+RLS), 9 (ordinary) |
| S3 Output egress | 3 (+extras) | 9, 10, 11 |
| G1 Tool authz | 5 | 9 (tools scoped via user) |
| G2 Retrieved-content injection | 4 | 12 |
| G3 Second-order injection | 6 | — |
| G4 Error/stack leak | 3 | 11 |
| G5 Logging | (extras on 1,2) | 9, 11 |
| Prompt-level defense = FAIL | 1, 2 | — |

Stacks: FastAPI (1, 5, 9), Express (2, 6, 11), Next.js (3, 7, 10), Django (4, 12), Go (8).
