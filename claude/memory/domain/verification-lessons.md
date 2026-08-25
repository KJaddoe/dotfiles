# Verification lessons: proving work is actually done

Rationale and history behind the binding rules in `~/.claude/CLAUDE.md` ("verify against the actual
code, don't reason from names or assumptions"; "evidence before assertions"). Each entry below is a
real correction, kept because the failure mode recurs.

Collected into global memory 2026-08-17. All six were learned on one client project but none of
them are specific to it. Keep client details out of this file (it is in the public dotfiles repo).

## Verify at the layer the user judges, not the layer that's easy

Claiming "nothing is editable in view mode" because `form.disable()` runs off a signal is reasoning
from the model layer. The user's answer: **"if I can change what I see in an input then it's
editable"**, and pressing Edit made ten inputs typeable. The model state was not evidence about
what a person can do.

The same trap has a visual half: `readonly` and `disabled` render completely differently, so
"behaves read-only" does not mean "reads as read-only". And a `curl` of an SSR page proves the
component renders server-side: it proves nothing about an app whose auth guard runs **client-side**,
where a real browser redirects to login instead.

**Apply:** probe the real DOM across every relevant state. Say "compile/render check", never
"verified live", when that is what you actually did. Unit tests, lint and i18n stay valid evidence,
just don't inflate them into "live".

## Tick a criterion only against something exercised, and name the evidence

Proposing to tick 14 of 17 acceptance criteria on the strength of 315 passing tests; only **5**
survived an honest re-read. Green tests prove the code does what it was told to do, not that it
works against the real system. The clearest case: sort headers were live and reordered nothing,
because the API silently stripped the unknown `sort` param instead of rejecting it, and a tick would
have hidden a failure that produces no error at all.

**Apply:** name the evidence inline ("observed live", "tool-verified", "structural, no component
imports HttpClient"). Distinguish *runtime* claims (need a live run), *structural* claims (code
inspection suffices) and *tool* claims (the tool's output suffices). Split a criterion rather than
half-ticking it.

## Assert the whole feature's invariant, not the delta you touched

Six defects in a row, each found after a "verified" fix. Every check was real; every one was scoped
to what had just changed: the dragged column but not its neighbours, the widths but not the
container, one drag direction but not both. A bug living in whatever isn't being looked at is
invisible by construction.

**Apply:** write the invariant once ("nothing leaves the viewport, nothing clips, columns left of
the handle don't move, the total fits the container") and it catches every future round.

Two traps from the same day: **unit tests, lint and format never build for release**, only the
production build caught a bundle-budget failure that would have shipped. And **a passing test can
pass for the wrong reason**: `activeElement.textContent` contained the expected string while focus
never moved, because `activeElement` fell back to `<body>`, whose textContent is the whole page.
Assert the specific node. Verify a fix isn't vacuous by breaking the behaviour and confirming the
exact expected tests fail, then restoring.

## Question the premises you inherit

During refinement, three question-rounds went into resolving a claims *namespace*, a decision that
existed only because the issue proposed a "fast-path so nav can render before `/me` resolves". The
question "why would we need that?" dissolved the whole thread: it bought one avoided round-trip and
cost a second source of truth for authorization, staleness by design, and an unowned decision. The
same pass found issues citing README sections that don't exist.

**Apply:** before turning an issue's open questions into questions for the user, check whether each
is downstream of a design choice that deserves challenging, and whether its cited sources exist. A
question that disappears when a bad premise is dropped beats a question answered well. Pushback on a
premise is a signal to re-derive, not to defend.

## When told to match a reference, open the reference

Claiming a rebuilt card "matched the original" after reconstructing it from a memory-summary snippet
of a *deleted* component and eyeballing the result. It looked nothing like the original, which still
existed on `main`.

**Apply:** render the original, render yours, compare concrete attributes (layout, spacing, colour,
typography, which fields, order, actions). Files can match while browsers differ: fonts, CSS
specificity, encapsulation, theme overrides, breakpoints, missing assets. Rendered pixels are ground
truth; markup similarity is a weak signal.

Corollary for styling: the **neighbouring component is the style guide**, not the spec. Three
consecutive visual mismatches came from building each page from a design spec that describes
structure and behaviour and says nothing about the visual treatment the app already settled on. Open
the closest existing equivalent and read its stylesheet and template first.

## A cheap gap is not a constraint

A spec filed "no sorting" under *constraints the API imposes, these are not choices*, beside
genuinely immovable gaps. The verified facts were right; the framing was wrong, and the same
document's follow-ups section contradicted it by calling the fix "small". A spec that mislabels a
cheap gap as a hard limit gets a feature descoped for no reason.

**Apply:** separate *the system does not do X* (a prerequisite with an owner) from *X is impossible*
(a constraint). Before declaring a capability unavailable, read the **upstream provider's** docs, not
just our wrapper's code: our shape is a choice, the provider's is the actual limit. Cross-check the
follow-ups list against the constraints list: if a follow-up says "small", it is not a constraint.
