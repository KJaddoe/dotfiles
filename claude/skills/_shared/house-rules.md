# House Rules

Cross-cutting constraints from the user's global `~/.claude/CLAUDE.md`. Every skill in this
directory is subordinate to them: where a skill's own wording below conflicts with these, the
rule here wins.

## Comments are earned, not owed

Before writing a doc-comment or inline comment, draft it, then delete the draft and re-read the
declaration or line alone. If nothing is lost, meaning the name, signature, and body (or the
surrounding code) already say what the draft said, skip it. Write one only when it carries
something the code cannot show on its own: units, ranges, what null means, a load-bearing
ordering, a workaround for an upstream quirk, a failure mode, or what a thing is for when its name
says only what it is. Constructors and framework lifecycle hooks get no block by default. Config
files stay comment-free.

## Search before writing

Before writing a function, component, or helper, search for one that already does the job, by
behavior, not by name, outside the current folder (shared/common/utils, the core lib, the
project's own conventions). Never write a new one alongside one you found. Widen the search past
the project before writing custom code: the language's stdlib and the platform's own features
beat a hand-rolled solution. If none exists and you need it a second time, extract it to shared
code rather than duplicating it.

## Inline execution by default

Default to doing the work yourself, in the current session, rather than spawning subagents for
routine or bounded work. Reach for a subagent only for genuinely open-ended or multi-step work
where the shape of the solution isn't already decided, or when the user asks for it.
