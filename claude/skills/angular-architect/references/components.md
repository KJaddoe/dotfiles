# Components & Signals

File and class names below follow the current Angular CLI schematic (since Angular 20): no
`.component` file suffix, no `Component` class suffix, `standalone: true` omitted (it's the only
option). An older project may still use the `.component.ts`/`XxxComponent` convention throughout,
in which case match that project's existing files over what's shown here.

## Component Pattern

```typescript
import { ChangeDetectionStrategy, Component, signal, computed, effect } from '@angular/core';

@Component({
  selector: 'app-user-profile',
  templateUrl: './user-profile.html',
  styleUrl: './user-profile.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserProfile {
  count = signal(0);
  doubleCount = computed(() => this.count() * 2);

  constructor() {
    effect(() => {
      console.log(`Count is: ${this.count()}`);
    });
  }

  increment() {
    this.count.update(value => value + 1);
  }
}
```

## Input/Output with Signals

```typescript
import { Component, input, output, model } from '@angular/core';

@Component({
  selector: 'app-search-box',
  template: `
    <input
      [value]="query()"
      (input)="onQueryChange($event)"
      [placeholder]="placeholder()" />
  `
})
export class SearchBox {
  // Signal inputs (Angular 17.1+)
  placeholder = input<string>('Search...');
  initialQuery = input<string>('');

  queryChange = output<string>();

  // Two-way binding with model signal
  query = model<string>('');

  onQueryChange(event: Event) {
    const value = (event.target as HTMLInputElement).value;
    this.query.set(value);
    this.queryChange.emit(value);
  }
}

// Parent usage
@Component({
  imports: [SearchBox],
  template: `
    <app-search-box
      [(query)]="searchQuery"
      [placeholder]="'Find users...'"
      (queryChange)="onSearch($event)" />
  `
})
export class SearchBoxHost {
  searchQuery = signal('');

  onSearch(query: string) {
    console.log('Searching:', query);
  }
}
```

## Smart vs Dumb Components

```typescript
import { rxResource } from '@angular/core/rxjs-interop';

// Smart Component (Container) - resource() replaces a manual subscribe() in a
// constructor/effect(): no unsubscribe to manage, and .value()/.isLoading()/.error() are signals
@Component({
  selector: 'app-users-container',
  imports: [UserList],
  template: `
    <app-user-list
      [users]="usersResource.value() ?? []"
      [loading]="usersResource.isLoading()"
      (userSelected)="onUserSelected($event)" />
  `
})
export class UsersContainer {
  private usersService = inject(UsersService);

  usersResource = rxResource({
    stream: () => this.usersService.getUsers(),
  });

  onUserSelected(user: User) {
    // Handle business logic
  }
}

// Dumb Component (Presentational)
@Component({
  selector: 'app-user-list',
  template: `
    @if (loading()) {
      <div>Loading...</div>
    } @else {
      @for (user of users(); track user.id) {
        <div (click)="userSelected.emit(user)">
          {{ user.name }}
        </div>
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UserList {
  users = input.required<User[]>();
  loading = input<boolean>(false);
  userSelected = output<User>();
}
```

## Content Projection

```typescript
// Card component with multiple slots - :host is the card, no wrapper div or
// class needed; header/footer use semantic elements, styled under :host in the SCSS
@Component({
  selector: 'app-card',
  template: `
    <header>
      <ng-content select="[header]"></ng-content>
    </header>
    <ng-content></ng-content>
    <footer>
      <ng-content select="[footer]"></ng-content>
    </footer>
  `
})
export class Card {}

// Usage
@Component({
  imports: [Card],
  template: `
    <app-card>
      <h2 header>Card Title</h2>
      <p>Card content goes here</p>
      <button footer>Action</button>
    </app-card>
  `
})
export class CardHost {}
```

## Dependency Injection

```typescript
import { Component, inject } from '@angular/core';
import { UserService } from './user.service';

@Component({
  selector: 'app-user-dashboard',
})
export class UserDashboard {
  // Modern inject() API
  private userService = inject(UserService);
  private router = inject(Router);

  // Optional dependency
  private logger = inject(LoggerService, { optional: true });

  users = signal<User[]>([]);

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.userService.getUsers().subscribe({
      next: users => this.users.set(users),
      error: err => this.logger?.error('Failed to load users', err)
    });
  }
}
```

## New Control Flow (@if, @for)

```typescript
@Component({
  template: `
    <!-- @if instead of *ngIf -->
    @if (user(); as currentUser) {
      <div>Hello, {{ currentUser.name }}</div>
    } @else if (loading()) {
      <div>Loading...</div>
    } @else {
      <div>Please log in</div>
    }

    <!-- @for instead of *ngFor -->
    @for (item of items(); track item.id) {
      <div>{{ item.name }}</div>
    } @empty {
      <div>No items found</div>
    }

    <!-- @switch instead of *ngSwitch -->
    @switch (status()) {
      @case ('pending') {
        <span>Pending...</span>
      }
      @case ('success') {
        <span>Success!</span>
      }
      @default {
        <span>Unknown</span>
      }
    }
  `
})
export class ModernControlFlow {
  user = signal<User | null>(null);
  loading = signal(false);
  items = signal<Item[]>([]);
  status = signal<'pending' | 'success' | 'error'>('pending');
}
```

## Performance: OnPush & TrackBy

```typescript
@Component({
  selector: 'app-product-list',
  template: `
    @for (product of products(); track trackByProductId($index, product)) {
      <app-product-card [product]="product" />
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ProductList {
  products = input.required<Product[]>();

  // TrackBy for optimal rendering
  trackByProductId(index: number, product: Product): number {
    return product.id;
  }
}
```

## Quick Reference

| Pattern           | Modern Angular Approach                        |
|-------------------|------------------------------------------------|
| File/class naming | `foo.ts` / `Foo` - no suffix (v20+)            |
| Component         | Standalone (only option, no flag)              |
| State             | Signals (`signal()`, `computed()`)             |
| Input             | `input()`, `input.required()`                  |
| Output            | `output<T>()`                                  |
| Two-way           | `model<T>()`                                   |
| DI                | `inject()` function                            |
| Control Flow      | `@if`, `@for`, `@switch`                       |
| Change Detection  | `ChangeDetectionStrategy.OnPush` (add by hand) |
