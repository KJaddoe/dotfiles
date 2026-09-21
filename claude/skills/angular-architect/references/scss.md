# Component SCSS

## Nest selectors to mirror the DOM

A component's SCSS structure should follow its template's real element tree, not a flat list of
classes. Given this template:

```html
<nav>
  <ul>
    <li *ngFor="let item of items()" [class.active]="item.active">
      <a [href]="item.href">{{ item.label }}</a>
    </li>
  </ul>
</nav>
```

nest the SCSS the same way, and use `&` for state/variant selectors instead of a separate
top-level rule:

```scss
:host {
  nav {
    ul {
      li {
        &.active {
          font-weight: 600;
        }

        a {
          color: var(--text-color);

          &:hover {
            text-decoration: underline;
          }
        }
      }
    }
  }
}
```

## Prefer element/attribute selectors over classes

Reach for a class only when no element, structural, or attribute selector can target the node.
Style semantic elements (`section`, `h2`, `ul`/`li`, `small`, `header`, `footer`) and
component/attribute selectors (`mat-toolbar`, `[role="alert"]`) directly, nested under `:host` or
a single scoping ancestor. Component style encapsulation already scopes these selectors, so this
does not leak into other components.

## Grouped selectors for styles shared across two branches

When a style would otherwise be duplicated across two DOM branches, don't flatten it to a shared
top-level class. List both parent chains in one grouped selector and nest the shared declarations
once, keeping each branch's unique styling in its own nested block:

```scss
.panel-header,
a.list-item {
  .icon,
  .title {
    color: var(--text-secondary-color);
  }
}
```

## What this replaces

Avoid wrapping every templated element in its own class, then styling those classes as flat,
un-nested top-level rules:

```scss
/* Don't: flat, class-per-element, no DOM relationship visible */
.card { }
.card-header { }
.card-body { }
.card-footer { }
```

The nested, element-selector form above keeps the stylesheet's structure legible as a map of the
template, and drops the classes that carried no styling purpose beyond hanging a hook off every
node.
