# Code quality gate: rules and why they were added

FYI/rationale file. Binding rule lives in `~/.claude/CLAUDE.md` -> Code quality.

## The gate (2026-07-13)

(1) Format touched code with the project's formatter, else a locally available one; never
mass-reformat untouched lines/files. (2) Lint every change with the project's linter, else a local
one; if the project has NO linting, notify the user and propose options rather than skip. (3) Drive
lint messages toward zero: fix root causes, don't blanket-suppress (`eslint-disable`,
`#pragma warning disable`, `any`); justify any unavoidable suppression. (4) Write tests when
possible; if no test setup, notify and propose options. (5) Definition of done = format + lint +
tests all green, reported honestly (say so if anything fails or was skipped); on a large/slow suite
run the changed-scope/affected tests each time (stating the scope run) and the full suite only when
cheap or before merge/release. (6) Commit any formatter/linter/test config introduced, keeping
mac/linux parity. Why: the user wants a consistently higher baseline and to be told, with options,
when a project lacks linting/testing instead of having it silently skipped.

## Best practices adopted (2026-07-13, all four offered, user picked all)

(1) Follow the codebase's existing conventions: read surrounding code first, mirror its
patterns/naming/libraries, reuse existing helpers, no new dependency or parallel approach without
sign-off (the highest-value lever: fit the codebase, don't reinvent). (2) Never hardcode secrets in
source (env/config/secret store). (3) Leave the tree clean: delete dead/commented-out code and debug
artifacts introduced (stray logging, `debugger`, throwaway TODOs). (4) Input & injection safety:
validate external input, parameterized queries not string-built SQL, escape output.

## Two more (2026-07-13, after reviewing the stacks worked on often)

(1) Don't swallow errors: no empty catch/silent fallback, surface or handle meaningfully, log with
context, fail loud/early. (2) Scripts and automation (ansible, dotbot, migrations, version pinning)
must be idempotent and safe to re-run (guard on state, expect `changed=0`), grounded in the
mise-migration ansible work. The biggest remaining gap is .NET/C# backend conventions, but those are
stack-specific and belong in that project's own `CLAUDE.md` (the user declined a starter template).

## Test-coverage bar made explicit (2026-07-21)

"Write tests when possible" was too loose: every suite must cover three kinds of case, each at the
layer where it's real: (1) the happy path; (2) edge/boundary cases; (3) what must NOT work and must
stay broken (authorization/access denials, invalid or malformed input rejection, abuse/injection).
Split by layer: server-side = SQL injection + authz bypass; client-side = output-escaping/XSS,
authz-gated UI, input rejection. When a bug or bad input is found, lock it out with a regression test
asserting it stays rejected, since the negative/must-stay-broken cases are the ones most often
skipped.

## Provenance-gate resolution (2026-08-05)

Eleven menu-origin rules were flagged by a provenance gate on 2026-08-04. Deciding test: origin FLAGS
a rule, it does not convict it; what decides is whether it changes behaviour that would otherwise go
wrong. Eight were kept (several already in use for weeks). Three were acted on: CHANGELOG was cut from
`CLAUDE.md` entirely (the `writing-project-docs` skill owns it); idempotency was demoted to the
dotfiles repo's own `CLAUDE.md` (one project, fails the 3+ promotion test, the migrations half lost
global coverage deliberately); dependency audit was converted to a pre-commit notice per the file's
own gate that a check beats prose. These three are not to be re-raised; the gate governs new rules
from here.

## Two rules sharpened after an invisible breakage (2026-08-20)

A client web app's ETag / conditional-request (`If-None-Match` -> 304) handling stopped working
because the edit that broke it was never requested AND the path was never exercised against a live
response. (1) Definition of done: green tests are evidence about the tests, not the system. Anything
crossing a real boundary (HTTP/API, DB, cache/CDN or conditional-request headers, auth, queue,
filesystem) counts as working only after being exercised with the actual response quoted
(status/headers/rows/output); if it can't be run, say "unverified: needs a real call", never
"working". (2) Scope: every hunk must trace to the request or to a gate it must pass
(format/lint/test/docs); working code not asked about stays untouched (no drive-by
refactors/renames/"while I'm here" cleanups); anything out of scope worth changing is raised as an
AskUserQuestion prompt, never buried in prose, and no permission mode ever counts as that answer. Why
both: the pre-existing gates were all command-output gates, so a green mocked suite satisfied them
completely while live behaviour was broken; and the scope rule fired at commit time, so an
unrequested edit inside a file already being edited never looked like bundling. Rule (1) catches the
consequence, rule (2) the cause; neither alone closes it. Binding copies span both CLAUDE.md -> Code
quality (Definition of done) and Working method (scope).

## Stdlib/native preference (2026-09-02)

Evaluated DietrichGebert/ponytail (an always-on "laziest solution that works" ruleset) and declined
it: six of its seven ladder rungs already existed here as sharper rules, and its testing stance (one
runnable check, no per-function suites) plus "fewest files possible" contradict the test-coverage,
docs-in-the-same-commit, and Angular-CLI rules. Adopted the one real gap: prefer the stdlib and
native platform features over custom code even when an already-installed dependency could do the job,
since the existing SEARCH rule stopped at the project boundary and the stdlib check only fired when
ADDING a dependency. Do not re-propose ponytail or a similar always-on minimalism plugin.
