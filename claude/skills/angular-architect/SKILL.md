---
name: angular-architect
description: Use when building Angular applications with standalone components or signals, setting up NgRx stores, establishing RxJS reactive patterns, performance tuning, or writing Angular tests for enterprise apps. Invoke for advanced routing with lazy loading and guards, NgRx state management, RxJS patterns, or bundle performance optimization.
license: Complete terms in LICENSE.txt
---

> Apply the [house rules](../_shared/house-rules.md) first: comments are earned not owed, search for existing code before writing new, default to inline execution over subagents.

# Angular Architect

Senior Angular architect specializing in current-standard Angular (standalone components, signals) and enterprise-grade application development. Before writing code, check the target project's installed Angular version (`package.json`) and match its existing conventions; where the project has no established convention yet, default to the latest stable Angular release's recommended patterns, not a pinned older version.

The Angular CLI schematic itself changed: since Angular 20, `ng generate component foo` writes `foo.ts`/`foo.html`/`foo.scss` and a class named `Foo`, not `foo.component.ts` and `FooComponent` - the `.component` file suffix, the `Component` class suffix, and `standalone: true` (standalone is the only option now) are no longer part of the generated output. An older project may still use the old suffix convention throughout; match that project's existing files over the CLI's current default. Where nothing established exists yet, generate via the CLI and trust what it actually produces rather than a hardcoded example - the examples in this skill use the current, unsuffixed convention.

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

## Key Patterns

### Component with OnPush and Signals

```typescript
import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

@Component({
  selector: 'app-user-card',
  imports: [],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h2>{{ fullName() }}</h2>
    <button (click)="onSelect()">Select</button>
  `,
})
export class UserCard {
  firstName = input.required<string>();
  lastName = input.required<string>();
  selected = output<string>();

  fullName = computed(() => `${this.firstName()} ${this.lastName()}`);

  onSelect(): void {
    this.selected.emit(this.fullName());
  }
}
```

The CLI does not add `changeDetection: ChangeDetectionStrategy.OnPush` on its own - add it by hand on every component.

### RxJS Subscription Management with `takeUntilDestroyed`

```typescript
import { Component, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { UserService } from './user.service';

@Component({ selector: 'app-users', template: `...` })
export class Users implements OnInit {
  private userService = inject(UserService);
  // DestroyRef is captured at construction time for use in ngOnInit
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.userService.getUsers()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (users) => { /* handle */ },
        error: (err) => console.error('Failed to load users', err),
      });
  }
}
```

### Reactive Form with `nonNullable` Controls

```typescript
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

@Component({
  selector: 'app-user-form',
  imports: [ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <input formControlName="firstName" />
      <input formControlName="lastName" />
      <button type="submit" [disabled]="form.invalid">Save</button>
    </form>
  `,
})
export class UserForm {
  private fb = inject(FormBuilder);

  form = this.fb.nonNullable.group({
    firstName: ['', Validators.required],
    lastName: ['', Validators.required],
  });

  onSubmit(): void {
    if (this.form.valid) {
      const { firstName, lastName } = this.form.getRawValue();
      // handle submit
    }
  }
}
```

### NgRx Action / Reducer / Selector

```typescript
// actions
export const loadUsers = createAction('[Users] Load Users');
export const loadUsersSuccess = createAction('[Users] Load Users Success', props<{ users: User[] }>());
export const loadUsersFailure = createAction('[Users] Load Users Failure', props<{ error: string }>());

// reducer
export interface UsersState { users: User[]; loading: boolean; error: string | null; }
const initialState: UsersState = { users: [], loading: false, error: null };

export const usersReducer = createReducer(
  initialState,
  on(loadUsers, (state) => ({ ...state, loading: true, error: null })),
  on(loadUsersSuccess, (state, { users }) => ({ ...state, users, loading: false })),
  on(loadUsersFailure, (state, { error }) => ({ ...state, error, loading: false })),
);

// selectors
export const selectUsersState = createFeatureSelector<UsersState>('users');
export const selectAllUsers = createSelector(selectUsersState, (s) => s.users);
export const selectUsersLoading = createSelector(selectUsersState, (s) => s.loading);
```

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
