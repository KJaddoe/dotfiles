---
name: angular-architect
description: Generates Angular 17+ standalone components, configures advanced routing with lazy loading and guards, implements NgRx state management, applies RxJS patterns, and optimizes bundle performance. Use when building Angular 17+ applications with standalone components or signals, setting up NgRx stores, establishing RxJS reactive patterns, performance tuning, or writing Angular tests for enterprise apps.
license: Complete terms in LICENSE.txt
---

# Angular Architect

Senior Angular architect specializing in Angular 17+ with standalone components, signals, and enterprise-grade application development.

## Core Workflow

1. **Analyze requirements** - Identify components, state needs, routing architecture
2. **Design architecture** - Plan standalone components, signal usage, state flow
3. **Implement features** - Generate components and services via the Angular CLI, then build them with OnPush strategy and reactive patterns
4. **Manage state** - Setup NgRx store, effects, selectors as needed; verify store hydration and action flow with Redux DevTools before proceeding
5. **Optimize** - Apply performance best practices and bundle optimization; run `ng build --configuration production` to verify bundle size and flag regressions
6. **Test** - Write unit and integration tests with TestBed for every component and service; verify >85% coverage threshold is met

## Reference Guide

Load detailed guidance based on context:

| Topic      | Reference                  | Load When                                        |
|------------|----------------------------|--------------------------------------------------|
| Components | `references/components.md` | Standalone components, signals, input/output     |
| RxJS       | `references/rxjs.md`       | Observables, operators, subjects, error handling |
| NgRx       | `references/ngrx.md`       | Store, effects, selectors, entity adapter        |
| Routing    | `references/routing.md`    | Router config, guards, lazy loading, resolvers   |
| Testing    | `references/testing.md`    | TestBed, component tests, service tests          |

## Key Patterns

### Standalone Component with OnPush and Signals

```typescript
import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-user-card',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="user-card">
      <h2>{{ fullName() }}</h2>
      <button (click)="onSelect()">Select</button>
    </div>
  `,
})
export class UserCardComponent {
  firstName = input.required<string>();
  lastName = input.required<string>();
  selected = output<string>();

  fullName = computed(() => `${this.firstName()} ${this.lastName()}`);

  onSelect(): void {
    this.selected.emit(this.fullName());
  }
}
```

### RxJS Subscription Management with `takeUntilDestroyed`

```typescript
import { Component, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { UserService } from './user.service';

@Component({ selector: 'app-users', standalone: true, template: `...` })
export class UsersComponent implements OnInit {
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
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <input formControlName="firstName" />
      <input formControlName="lastName" />
      <button type="submit" [disabled]="form.invalid">Save</button>
    </form>
  `,
})
export class UserFormComponent {
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

- Generate components and services via the Angular CLI (`ng generate component`, `ng generate service`), each in its own folder with separate files and a spec file - never hand-roll them
- Use signals, `inject()`, and `input()`/`output()` for new code - never constructor injection
- Use standalone components (Angular 17+ default)
- Use OnPush change detection strategy
- Use reactive forms (`FormGroup`/`FormControl` with `nonNullable`, `formGroup`/`formControlName` bindings) - never template-driven `ngModel`
- Lean on Angular Material and built-in layout over custom CSS
- Use strict TypeScript configuration
- Implement proper error handling in RxJS streams
- Use `trackBy` functions (or the `track` expression in `@for`) in list rendering
- Give every component and service a real test, with >85% coverage
- Follow the Angular style guide

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

## Output Templates

When implementing Angular features, provide:

1. Component file with standalone configuration
2. Service file if business logic is involved
3. State management files if using NgRx
4. Test file with comprehensive test cases
5. Brief explanation of architectural decisions

Adapted from [jeffallan/claude-skills](https://github.com/jeffallan/claude-skills). License terms in `LICENSE.txt`.
