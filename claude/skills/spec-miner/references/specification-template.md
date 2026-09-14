# Specification Template

## Full Template

```markdown
# Reverse-Engineered Specification: [System/Feature Name]

## Overview
[High-level description based on analysis]

## Architecture Summary

### Technology Stack
- **Language**: TypeScript 5.x
- **Framework**: NestJS 10.x
- **Database**: PostgreSQL 15
- **ORM**: Prisma 5.x

### Module Structure
```

src/
├── auth/         # Authentication (JWT, guards)
├── users/        # User CRUD operations
├── orders/       # Order processing
└── common/       # Shared utilities

```markdown

### Data Flow
```

Request → Guard → Controller → Service → Repository → Database
                                     ↓
                              External APIs

```markdown

## Observed Functional Requirements

### [Module Name]

**OBS_XXX_001**: [Feature Name]
[EARS format requirement]

**OBS_XXX_002**: [Feature Name]
[EARS format requirement]

## Observed Non-Functional Requirements

### Security
- JWT tokens signed with RS256
- Passwords hashed with bcrypt (12 rounds)
- Rate limiting: 100 req/min per IP

### Performance
- Database connection pool: 10 connections
- Response timeout: 30 seconds
- Pagination: default 20, max 100

### Error Handling
| Code | Condition             | Response                             |
|------|-----------------------|--------------------------------------|
| 400  | Validation failure    | `{ error: string, details: object }` |
| 401  | Invalid/missing token | `{ error: "Unauthorized" }`          |
| 404  | Resource not found    | `{ error: "Not found" }`             |
| 500  | Unhandled error       | `{ error: "Internal server error" }` |

## Inferred Acceptance Criteria

### AC_001: [Feature]
Given [precondition]
When [action]
Then [expected result]

## Uncertainties and Questions

- [ ] What triggers order status transitions?
- [ ] Is soft delete implemented for users?
- [ ] What external APIs are called?
- [ ] Are there background jobs?

## Recommendations

1. Add OpenAPI documentation to controllers
2. Missing input validation on PATCH endpoints
3. Consider adding request tracing
```

## Output Location

Save the specification to the untracked session specs directory (`~/.claude/projects/<mapped-path>/specs/{project_name}_reverse_spec.md`), not committed to the repo unless asked.

## Required Sections

| Section                 | Purpose                          |
|-------------------------|----------------------------------|
| Overview                | High-level summary               |
| Architecture            | Tech stack, structure, data flow |
| Functional Requirements | EARS format observations         |
| Non-Functional          | Security, performance, errors    |
| Acceptance Criteria     | Given/When/Then format           |
| Uncertainties           | Questions for clarification      |
| Recommendations         | Improvements identified          |
