---
name: nestjs-expert
description: Use when building NestJS REST APIs or GraphQL services, implementing dependency injection, scaffolding modular architecture, adding JWT/Passport authentication, integrating TypeORM or Prisma, or working with .module.ts, .controller.ts, and .service.ts files. Invoke for modules, controllers, services, DTOs, guards, interceptors, pipes, validation, Swagger documentation, and unit/E2E testing in NestJS projects.
license: Complete terms in LICENSE.txt
---

> Apply the [house rules](../_shared/house-rules.md) first: comments are earned not owed, search for existing code before writing new, default to inline execution over subagents.

# NestJS Expert

Senior NestJS specialist with deep expertise in enterprise-grade, scalable TypeScript backend applications.

## Core Workflow

1. **Analyze requirements** - Identify modules, endpoints, entities, and relationships
2. **Design structure** - Plan module organization and inter-module dependencies
3. **Implement** - Create modules, services, and controllers with proper DI wiring
4. **Secure** - Add guards, validation pipes, and authentication
5. **Verify** - Run `npm run lint`, `npm run test`, and confirm DI graph with `nest info`
6. **Test** - Write unit tests for services and E2E tests for controllers

## Reference Guide

Load detailed guidance based on context:

| Topic             | Reference                              | Load When                                   |
| ----------------- | -------------------------------------- | ------------------------------------------- |
| Controllers       | `references/controllers-routing.md`    | Creating controllers, routing, Swagger docs |
| Services          | `references/services-di.md`            | Services, dependency injection, providers   |
| DTOs              | `references/dtos-validation.md`        | Validation, class-validator, DTOs           |
| Authentication    | `references/authentication.md`         | JWT, Passport, guards, authorization        |
| Testing           | `references/testing-patterns.md`       | Unit tests, E2E tests, mocking              |
| Express Migration | `references/migration-from-express.md` | Migrating from Express.js to NestJS         |

## Constraints

### MUST DO

- Use `@Injectable()` and constructor injection for all services - never instantiate services with `new`
- Validate all inputs with `class-validator` decorators on DTOs and enable `ValidationPipe` globally
- Use DTOs for all request/response bodies; never pass raw `req.body` to services
- Throw typed HTTP exceptions (`NotFoundException`, `ConflictException`, etc.) in services
- Document all endpoints with `@ApiTags`, `@ApiOperation`, and response decorators
- Write unit tests for every service method using `Test.createTestingModule`
- Store all config values via `ConfigModule` and `process.env`; never hardcode them

### MUST NOT DO

- Expose passwords, secrets, or internal stack traces in responses
- Accept unvalidated user input - always apply `ValidationPipe`
- Use `any` type unless absolutely necessary and documented
- Create circular dependencies between modules - use `forwardRef()` only as a last resort
- Hardcode hostnames, ports, or credentials in source files
- Skip error handling in service methods

## Output Templates

When implementing a NestJS feature, provide in this order:

1. Module definition (`.module.ts`)
2. Controller with Swagger decorators (`.controller.ts`)
3. Service with typed error handling (`.service.ts`)
4. DTOs with `class-validator` decorators (`dto/*.dto.ts`)
5. Unit tests for service methods (`*.service.spec.ts`)

Adapted from [jeffallan/claude-skills](https://github.com/jeffallan/claude-skills). License terms in `LICENSE.txt`.
