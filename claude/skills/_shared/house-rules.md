# House Rules

Cross-cutting constraints from the user's global `~/.claude/CLAUDE.md`. Every skill in this
directory is subordinate to them: where a skill's own wording below conflicts with these, the
rule here wins.

## Comments are earned, not owed

Doc-comments that the language's official standard requires are always written, in its syntax
and tag style. A required block still says what the thing is for, never merely its name. Per
language (a language missing here gets checked against its official source and added before its
first doc-comment is written):

- **TypeScript/JavaScript** (Google TypeScript style guide; TSDoc, TypeScript handbook): every
  top-level export, except symbols exported only for tooling (`@NgModule`). `@param`/`@returns`
  only where they add to the name and type; no types in them in `.ts` files, where TypeScript
  ignores them; no `@override`. In plain `.js` without TypeScript, JSDoc types are the type system.
- **C#** (Microsoft recommended XML documentation tags): every publicly visible type and member,
  at least a `<summary>`; `<inheritdoc/>` on overrides and interface implementations. Once any
  `<param>` is written, every parameter gets one; `<returns>`, and `<exception>` per exception.
- **Python** (PEP 257): every module, exported function and class, and public method including
  `__init__`. Arguments, return value, side effects and raised exceptions where applicable, in the
  project's docstring style. A one-liner keeps its closing quotes on the same line.
- **Shell** (Google Shell style guide): an overview comment at the top of every file; a header on
  every library function and every function that is not both obvious and short, giving a
  description plus whichever of Globals, Arguments, Outputs and Returns apply.
- **Go** (Go Doc Comments): every package and every exported name. `//` comments only, directly
  above the declaration, a full sentence starting with the declared name; parameters, results and
  errors are named in the prose, no tags.
- **Rust** (Rust API Guidelines): the crate (`//!`) and every public item (`///`), with an
  `# Examples` section, and `# Errors`, `# Panics` and `# Safety` wherever they apply; no
  per-parameter tags.
- **Java** (Google Java style guide): every public class and every public or protected member,
  except a self-explanatory one such as `getFoo()` and, where it adds nothing, an override. The
  summary is a fragment; block tags in the order `@param`, `@return`, `@throws`, never empty.
- **Kotlin** (Kotlin coding conventions, KDoc): no coverage rule of its own, so the earned test
  below applies. Parameters and return value go in the prose with `[name]` links; `@param` and
  `@return` only for a description too long for the flow of the text.
- **Swift** (Swift API Design Guidelines): every declaration. The summary is a sentence fragment;
  `- Parameter`/`- Parameters:`, `- Returns:` and `- Throws:` for anything beyond it.
- **Dart** (Effective Dart): most public API and the library itself, with `///`. The first
  sentence is the summary; parameters go in the prose with `[name]`, no `@param`/`@returns`.
- **C++** (Google C++ style guide): every non-obvious class, and almost every function
  declaration, private ones included, omitting only the simple and obvious ones. Describe inputs,
  outputs and failure behaviour; `//` is the common syntax.
- **PHP** (phpDocumentor; the PHP-FIG PHPDoc proposals are unfinished drafts): no coverage rule,
  so the earned test applies. `/** */` DocBlocks with `@param`, `@return` and `@throws`.
- **Ruby** (community Ruby style guide; no official one): no coverage rule, so the earned test
  applies. YARD syntax for what is written.
- **Lua** (no official standard; LuaLS annotations): the earned test applies. A written block
  gets a `---@param` per parameter and a `---@return` per return value.

For everything else, before writing a doc-comment or inline comment, draft it, then delete the
draft and re-read the declaration or line alone. If nothing is lost, meaning the name, signature,
and body (or the surrounding code) already say what the draft said, skip it. Write one only when
it carries something the code cannot show on its own: units, ranges, what null means, a
load-bearing ordering, a workaround for an upstream quirk, a failure mode, or what a thing is for
when its name says only what it is. Outside what the standard requires, constructors and
framework lifecycle hooks get no block by default. Config files stay comment-free.

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
