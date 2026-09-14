# EARS Format

## EARS Syntax

Easy Approach to Requirements Syntax for clear, unambiguous requirements.

### Basic Patterns

#### Ubiquitous (Always)

```text
The system shall [action].
```

#### Event-Driven

```text
When [trigger], the system shall [action].
```

#### State-Driven

```text
While [state], the system shall [action].
```

#### Conditional

```text
While [state], when [trigger], the system shall [action].
```

#### Optional

```text
Where [feature enabled], the system shall [action].
```

## Example Observations

### Authentication

#### OBS_AUTH_001: Login Flow

```text
While credentials are valid, when POST /auth/login is called,
the system shall return JWT access token (15m) and refresh token (7d).
```

#### OBS_AUTH_002: Token Refresh

```text
While refresh token is valid, when POST /auth/refresh is called,
the system shall issue new access token.
```

#### OBS_AUTH_003: Invalid Token

```text
When expired or invalid token is provided,
the system shall return 401 Unauthorized.
```

### User Management

#### OBS_USER_001: User Creation

```text
While email is unique, when POST /users is called with valid data,
the system shall create user with bcrypt-hashed password (rounds=12).
```

#### OBS_USER_002: Email Validation

```text
When email format is invalid,
the system shall return 400 with error message "Invalid email format".
```

### Input Validation

#### OBS_INPUT_001: Required Fields

```text
When required fields are missing,
the system shall return 400 with field-specific error messages.
```

## Quick Reference

| Type        | Pattern                    | Example Trigger          |
|-------------|----------------------------|--------------------------|
| Ubiquitous  | shall [action]             | Always true              |
| Event       | When [X], shall            | On button click          |
| State       | While [X], shall           | While logged in          |
| Conditional | While [X], when [Y], shall | While admin, when delete |
| Optional    | Where [X], shall           | If feature enabled       |
