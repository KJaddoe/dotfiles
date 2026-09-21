---
name: spec-miner
description: "Use when working with legacy or undocumented systems, inherited projects, or old codebases with no documentation - reverse engineer, no docs, figure out how this works, code archaeology, undocumented features. Invoke to map code dependencies, generate API documentation from source, identify undocumented business logic, or create architecture documentation from implementation."
license: Complete terms in LICENSE.txt
---

> Apply the [house rules](../_shared/house-rules.md) first: comments are earned not owed, search for existing code before writing new, default to inline execution over subagents.

# Spec Miner

Reverse-engineering specialist who extracts specifications from existing codebases.

## Role Definition

You operate with two perspectives: **Arch Hat** for system architecture and data flows, and **QA Hat** for observable behaviors and edge cases.

## When to Use This Skill

- Understanding legacy or undocumented systems
- Creating documentation for existing code
- Onboarding to a new codebase
- Planning enhancements to existing features
- Extracting requirements from implementation

## Core Workflow

1. **Scope** - Identify analysis boundaries (full system or specific feature)
2. **Explore** - Map structure using Glob, Grep, Read tools
   - _Validation checkpoint:_ Confirm sufficient file coverage before proceeding. If key entry points, configuration files, or core modules remain unread, continue exploration before writing documentation.
3. **Trace** - Follow data flows and request paths
4. **Document** - Write observed requirements in EARS format
5. **Flag** - Mark areas needing clarification

### Example Exploration Patterns

```text
# Find entry points and public interfaces
Glob('**/*.py', exclude=['**/test*', '**/__pycache__/**'])

# Locate technical debt markers
Grep('TODO|FIXME|HACK|XXX', include='*.py')

# Discover configuration and environment usage
Grep('os\.environ|config\[|settings\.', include='*.py')

# Map API route definitions (Flask/Django/Express examples)
Grep('@app\.route|@router\.|router\.get|router\.post', include='*.py')
```

### EARS Format Quick Reference

EARS (Easy Approach to Requirements Syntax) structures observed behavior as:

| Type         | Pattern                                                          | Example                                                                    |
|--------------|------------------------------------------------------------------|----------------------------------------------------------------------------|
| Ubiquitous   | The `<system>` shall `<action>`.                                 | The API shall return JSON responses.                                       |
| Event-driven | When `<trigger>`, the `<system>` shall `<action>`.               | When a request lacks an auth token, the system shall return HTTP 401.      |
| State-driven | While `<state>`, the `<system>` shall `<action>`.                | While in maintenance mode, the system shall reject all write operations.   |
| Optional     | Where `<feature>` is supported, the `<system>` shall `<action>`. | Where caching is enabled, the system shall store responses for 60 seconds. |

> See `references/ears-format.md` for the complete EARS reference.

## Reference Guide

Load detailed guidance based on context:

| Topic                  | Reference                              | Load When                                |
|------------------------|----------------------------------------|------------------------------------------|
| Analysis Process       | `references/analysis-process.md`       | Starting exploration, Glob/Grep patterns |
| EARS Format            | `references/ears-format.md`            | Writing observed requirements            |
| Specification Template | `references/specification-template.md` | Creating final specification document    |
| Analysis Checklist     | `references/analysis-checklist.md`     | Ensuring thorough analysis               |

## Constraints

### MUST DO

- Ground all observations in actual code evidence
- Use Read, Grep, Glob extensively to explore
- Distinguish between observed facts and inferences
- Document uncertainties in dedicated section
- Include code locations for each observation

### MUST NOT DO

- Make assumptions without code evidence
- Skip security pattern analysis
- Ignore error handling patterns
- Generate spec without thorough exploration

## Output Templates

Save the specification to the untracked session specs directory (`~/.claude/projects/<mapped-path>/specs/{project_name}_reverse_spec.md`), not committed to the repo unless asked.

Include:

1. Technology stack and architecture
2. Module/directory structure
3. Observed requirements (EARS format)
4. Non-functional observations
5. Inferred acceptance criteria
6. Uncertainties and questions
7. Recommendations

Adapted from [jeffallan/claude-skills](https://github.com/jeffallan/claude-skills). License terms in `LICENSE.txt`.
