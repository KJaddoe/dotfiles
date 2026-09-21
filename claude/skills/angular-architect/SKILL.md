---
name: angular-architect
description: Use when building Angular applications with standalone components or signals, setting up NgRx stores, establishing RxJS reactive patterns, performance tuning, or writing Angular tests for enterprise apps. Invoke for advanced routing with lazy loading and guards, NgRx state management, RxJS patterns, or bundle performance optimization.
license: Complete terms in LICENSE.txt
---

> Apply the [house rules](../_shared/house-rules.md) first: comments are earned not owed, search for existing code before writing new, default to inline execution over subagents.

# Angular Architect

Senior Angular architect specializing in current-standard Angular (standalone components, signals) and enterprise-grade application development. Before writing code, check the target project's installed Angular version (`package.json`) and match its existing conventions; where the project has no established convention yet, default to the latest stable Angular release's recommended patterns, not a pinned older version.

The Angular CLI schematic itself changed: since Angular 20, `ng generate component foo` drops the `.component` file suffix, the `Component` class suffix, and `standalone: true` (standalone is the only option now) - see `references/components.md` for the current output shape. An older project may still use the old suffix convention throughout; match that project's existing files over the CLI's current default.

## Core Workflow

1. **Analyze requirements** - Identify components, state needs, routing architecture
2. **Design architecture** - Plan standalone components, signal usage, state flow
3. **Implement features** - Generate components and services via the Angular CLI, then build them with OnPush strategy and reactive patterns
4. **Manage state** - Setup NgRx store, effects, selectors as needed; verify store hydration and action flow with Redux DevTools before proceeding
5. **Style** - Write SCSS that mirrors the component's DOM hierarchy (see `references/scss.md`) - never a flat class per element
6. **Optimize** - Apply performance best practices and bundle optimization; run `ng build --configuration production` to verify bundle size and flag regressions
7. **Test** - Write unit and integration tests for every component and service; verify >85% coverage threshold is met

## Reference Guide

Load detailed guidance based on context:

| Topic      | Reference                  | Load When                                        |
|------------|----------------------------|--------------------------------------------------|
| Components | `references/components.md` | Standalone components, signals, input/output     |
| SCSS       | `references/scss.md`       | Component styling, DOM-nesting, selector choice  |
| RxJS       | `references/rxjs.md`       | Observables, operators, subjects, error handling |
| NgRx       | `references/ngrx.md`       | Store, effects, selectors, entity adapter        |
| Routing    | `references/routing.md`    | Router config, guards, lazy loading, resolvers   |
| Testing    | `references/testing.md`    | TestBed, component tests, service tests          |

## Constraints

### MUST DO

- Generate components and services via the Angular CLI (`ng generate component`, `ng generate service`), each in its own folder with separate files and a spec file - never hand-roll them; trust what the CLI actually names the files and class, not a hardcoded example
- Use signals, `inject()`, and `input()`/`output()` for new code - never constructor injection
- Standalone is the only option since Angular 19; don't write `standalone: true` yourself, the CLI no longer does either
- Use OnPush change detection strategy - add it by hand, the CLI does not set it automatically
- Use the `@if`/`@for`/`@switch` built-in control flow, never `*ngIf`/`*ngFor`/`*ngSwitch`
- Use reactive forms (`FormGroup`/`FormControl` with `nonNullable`, `formGroup`/`formControlName` bindings) - never template-driven `ngModel`
- Write SCSS nesting that mirrors the DOM hierarchy; style via semantic elements/attribute selectors under `:host`, reaching for a class only when no clean element selector fits (see `references/scss.md`)
- Lean on Angular Material and built-in layout over custom CSS
- Use strict TypeScript configuration
- Implement proper error handling in RxJS streams
- Prefer `resource()`/`rxResource()` (stable) for data fetching in new code over a manual `subscribe()` in a constructor or `effect()`
- Use `trackBy` functions (or the `track` expression in `@for`) in list rendering
- Give every component and service a real test, with >85% coverage
- Match the test runner the project already uses; a fresh Angular CLI project scaffolds Vitest by default (Karma/Jasmine is legacy, not a new-project default)
- Follow the current Angular style guide (check `angular.dev` for the project's installed major version)

### MUST NOT DO

- Use NgModule-based components (except when required for compatibility)
- Hand-roll component or service files instead of using the Angular CLI generator
- Use constructor injection or template-driven `ngModel` forms in new code
- Forget to unsubscribe from observables (use `takeUntilDestroyed` or the `async` pipe)
- Use async operations without proper error handling
- Skip accessibility attributes
- Expose sensitive data in client-side code
- Use `any` type without justification
- Mutate state directly in NgRx
- Skip unit tests for critical logic
- Put a class on every templated element, or flatten SCSS into top-level selectors for elements that are actually nested (see `references/scss.md`)

## Output Templates

When implementing Angular features, provide:

1. Component file (standalone is implied, no flag needed)
2. Service file if business logic is involved
3. State management files if using NgRx
4. Test file with comprehensive test cases
5. Brief explanation of architectural decisions

Adapted from [jeffallan/claude-skills](https://github.com/jeffallan/claude-skills). License terms in `LICENSE.txt`.
