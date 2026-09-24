# Doc-comment style: current rule and why it changed seven times

FYI/rationale file. Binding rule lives in `~/.claude/CLAUDE.md` -> Code & artifacts. This file exists
because the rule went through seven corrections between 2026-07-13 and 2026-09-24 and the reasoning
for each is worth keeping, even though only the final state governs behaviour.

## Current rule (2026-09-24)

- What each language's official standard REQUIRES is written, in its syntax and tag style; the
  per-language list lives in `claude/skills/_shared/house-rules.md` and is not repeated here. A
  required block still says what the thing is FOR, never merely its name.
- Everything else is EARNED, not owed: write one only where it says what the declaration cannot
  (units, ranges, what null means, a load-bearing failure mode or ordering, or what a thing is FOR
  when its name only says what it is). There, constructors and framework lifecycle hooks get none
  by default. Test: delete a draft block and re-read the declaration; if nothing is lost, leave it
  deleted.
- Tags follow the standard (e.g. Kotlin, Dart and Go put parameters in the prose, C# lists every
  parameter once any is listed). The prose above the tags is capped (one line, three at the most);
  tag lines and a standard's required sections never count towards that cap.
- A tag-free summary that fits on one line may stay on one line (`/** Reads one contact. */`).
  Anything longer, or carrying a tag, is EXPANDED: opening delimiter alone on its line,
  star-prefixed continuations, closing delimiter alone, a bare star line between the prose and
  the tags.
- Inline `//` comments: never narrate a line, and never justify an obvious branch, guard, early
  return, or fallback either, since the code already says it. Test: delete and re-read; keep one
  only where a competent reader would otherwise make a WRONG change (a non-obvious ordering, an
  upstream workaround, a check that looks redundant beside another).

## Why it took seven passes

- 2026-06-01: the ancestor rule - no explanatory comments in code or config, matching each file's
  existing near-zero density. Still governs inline narration and config files.
- 2026-07-13: first doc-comment mandate - purpose + params + returns on EVERY function, class, and
  method. Produced comments that only restated the signature (a 3-param TS function got 6 comment
  lines).
- 2026-09-02: tightened to "as short as possible", with `@param`/`@returns` written only where they
  add what the signature cannot say. That made the tags conditional.
- 2026-09-03: the tags were made unconditional again (a block that exists always lists them; they
  are evidence of the contract, not restatement). The brevity ceiling was rescoped to the PROSE only.
- 2026-09-03: an EXPANDED layout was made explicit after a compact form (text starting on the opening
  delimiter) was applied across two client repos and rejected on sight. This axis had never actually
  been decided before; brevity governs how much is written, not how it's laid out.
- 2026-09-03: the whole "every function" absolute was inverted to "earned", tested against a class
  docblock, a constructor, a lifecycle hook, and a self-explanatory method that the strict mandate
  still forced blocks onto. A portal repo still carried 13 blocks on constructors/lifecycle hooks and
  76 blocks across 170 declarations after a dedicated cleanup pass done under the OLD rule.
- 2026-09-03 (measurement): comparing active repos showed block LENGTH predicts bloat, not
  comment-to-code ratio or block count. One repo's `application/ports/*.port.ts` hit 293%
  comment-to-code with no Swagger justification; another had MORE blocks (1078 vs 640) at an average
  of 3.0 lines and read fine. `@param`/`@returns` restatement was real but small (11-20% of comment
  lines), which is why the cap targets block length: a file of many small, individually-earned
  one-liners scores high on a ratio metric legitimately.
- 2026-09-24: checked against the official standards for every language with a skill (PEP 257,
  Google TypeScript, Shell, Java and C++ guides, Microsoft XML doc tags, Go Doc Comments, Rust API
  Guidelines, Kotlin conventions, Swift API Design Guidelines, Effective Dart, phpDocumentor, the
  Ruby style guide, LuaLS, TypeScript handbook, TSDoc). The user chose "we will follow the
  standards and best practices": required coverage per language now comes first, and the
  always-list-tags rule of 2026-09-03 is superseded for TypeScript, where Google makes redundant
  tags optional. This knowingly brings back one-line blocks on self-explanatory Angular exports.
- 2026-09-24: the user allowed single-line blocks per the standards (Google TypeScript and Java,
  Kotlin): a tag-free one-line summary may stay on one line. The 2026-09-03 expanded-layout
  correction still governs every block that is longer or carries a tag, which is what was
  rejected then (text beside the delimiters of a multi-line block).

## Enforcement

`claude/hooks/doc-comment-shape.py` checks the SHAPE of blocks that exist (tags present, layout
expanded). It deliberately does not judge restatement, which needs the name, the type, and the
domain at once, so that half stays a human judgement call rather than a hook.
