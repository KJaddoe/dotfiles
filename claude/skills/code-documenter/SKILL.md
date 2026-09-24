---
name: code-documenter
description: Use when adding docstrings to functions or classes, creating API documentation, building documentation sites, or writing tutorials and user guides. Invoke for OpenAPI/Swagger specs, JSDoc annotations, doc portals, or getting started guides.
license: Complete terms in LICENSE.txt
---

> Apply the [house rules](../_shared/house-rules.md) first: comments are earned not owed, search for existing code before writing new, default to inline execution over subagents.

# Code Documenter

Documentation specialist for inline documentation, API specs, documentation sites, and developer guides.

## When to Use This Skill

Applies to any task involving code documentation, API specs, or developer-facing guides. See the reference table below for specific sub-topics.

## Core Workflow

1. **Discover** - Ask for format preference and exclusions
2. **Detect** - Identify language and framework
3. **Analyze** - Find candidate declarations (functions, classes, methods, types) that have no doc-comment, or one that looks stale
4. **Gate** - A candidate the language's official standard requires documented (TypeScript/JavaScript top-level exports, C# public types and members, Python modules, exported functions and classes and public methods, shell file overviews and non-trivial functions) always passes; see the house rules. For every other candidate, draft the doc-comment, then delete the draft and re-read the declaration alone. If nothing is lost, meaning the name, signature, and body already say what the draft said, skip it: a doc-comment is earned, not owed. Write the block only when the draft carried something the declaration cannot show on its own: units, ranges, what null means, a load-bearing ordering, a failure mode, or what the thing is for when the name says only what it is. A class, function, or method whose name and signature already tell the whole story gets no block
5. **Document** - Apply a consistent format, but only to candidates the gate cleared
6. **Validate** - Test all code examples compile/run:
   - Python: `python -m doctest file.py` for doctest blocks; `pytest --doctest-modules` for module-wide checks
   - TypeScript/JavaScript: `tsc --noEmit` to confirm typed examples compile
   - OpenAPI: validate spec with `npx @redocly/cli lint openapi.yaml`
   - If validation fails: fix examples and re-validate before proceeding to the Report step
7. **Report** - Generate a coverage summary, including how many candidates the gate skipped and why

## Quick-Reference Examples

The following show format once the Gate step has confirmed a block is earned.

### Google-style Docstring (Python)

```python
def fetch_user(user_id: int, active_only: bool = True) -> dict:
    """Fetch a single user record by ID.

    Args:
        user_id: Unique identifier for the user.
        active_only: When True, raise an error for inactive users.

    Returns:
        A dict containing user fields (id, name, email, created_at).

    Raises:
        ValueError: If user_id is not a positive integer.
        UserNotFoundError: If no matching user exists.
    """
```

### NumPy-style Docstring (Python)

```python
def compute_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors.

    Parameters
    ----------
    vec_a : np.ndarray
        First input vector, shape (n,).
    vec_b : np.ndarray
        Second input vector, shape (n,).

    Returns
    -------
    float
        Cosine similarity in the range [-1, 1].

    Raises
    ------
    ValueError
        If vectors have different lengths.
    """
```

### JSDoc (TypeScript)

```typescript
/**
 * Fetches a paginated list of products from the catalog.
 *
 * @param {string} categoryId - The category to filter by.
 * @param {number} [page=1] - Page number (1-indexed).
 * @param {number} [limit=20] - Maximum items per page.
 * @returns {Promise<ProductPage>} Resolves to a page of product records.
 * @throws {NotFoundError} If the category does not exist.
 *
 * @example
 * const page = await fetchProducts('electronics', 2, 10);
 * console.log(page.items);
 */
async function fetchProducts(
  categoryId: string,
  page = 1,
  limit = 20
): Promise<ProductPage> { ... }
```

## Reference Guide

Load detailed guidance based on context:

| Topic                   | Reference                               | Load When                                            |
| ----------------------- | --------------------------------------- | ---------------------------------------------------- |
| Python Docstrings       | `references/python-docstrings.md`       | Google, NumPy, Sphinx styles                         |
| TypeScript JSDoc        | `references/typescript-jsdoc.md`        | JSDoc patterns, TypeScript                           |
| FastAPI/Django API      | `references/api-docs-fastapi-django.md` | Python API documentation                             |
| NestJS/Express API      | `references/api-docs-nestjs-express.md` | Node.js API documentation                            |
| Coverage Reports        | `references/coverage-reports.md`        | Generating documentation reports                     |
| Documentation Systems   | `references/documentation-systems.md`   | Doc sites, static generators, search, testing        |
| Interactive API Docs    | `references/interactive-api-docs.md`    | OpenAPI 3.1, portals, GraphQL, WebSocket, gRPC, SDKs |
| User Guides & Tutorials | `references/user-guides-tutorials.md`   | Getting started, tutorials, troubleshooting, FAQs    |

## Constraints

### MUST DO

- Ask for format preference before starting
- Detect framework for correct API doc strategy
- Run the earned-or-not gate on every candidate before writing a block
- Document only declarations the gate cleared: those the standard requires, and others where units, ranges, null handling, a load-bearing ordering, a failure mode, or purpose beyond the name would otherwise be lost
- Include parameter descriptions per the language standard: every parameter in C# and Python, and in TypeScript only where they add to the name and type; parameter types only where the language has no type syntax (plain JavaScript)
- Document exceptions/errors in every block that is written
- Test code examples in documentation
- Generate a coverage report that states gate skips alongside written docs

### MUST NOT DO

- Assume docstring format without asking
- Apply wrong API doc strategy for framework
- Write inaccurate or untested documentation
- Skip error documentation in a block that is written
- Write a block for a declaration the gate did not clear, including obvious non-public getters/setters
- Restate the name or signature in prose instead of adding what it cannot show
- Create documentation that's hard to maintain

## Output Formats

Depending on the task, provide:

1. **Code Documentation:** Documented files + coverage report (including gate skips)
2. **API Docs:** OpenAPI specs + portal configuration
3. **Doc Sites:** Site configuration + content structure + build instructions
4. **Guides/Tutorials:** Structured markdown with examples + diagrams

Adapted from [jeffallan/claude-skills](https://github.com/jeffallan/claude-skills). License terms in `LICENSE.txt`.
