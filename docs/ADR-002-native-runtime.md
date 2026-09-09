# ADR-002: Native runtime migration

**Status:** Accepted

**Date:** 2026-09-09

## Context

TajikLang began with a Python tree-walk interpreter. That was the right way
to learn language engineering and release a usable educational tool quickly,
but it should not be the permanent engine of a standalone programming
language.

## Decision

TajikLang will implement a standalone Rust runtime behind the same language
specification and conformance suite. Electron remains the cross-platform
Studio shell. The reference interpreter remains bundled until the native
runtime reaches feature parity.

## Options considered

| Option | Result |
| --- | --- |
| Keep only Python | Fast now, but weak long-term independence |
| Rewrite everything before release | Risks removing working language features |
| Parallel Rust runtime with conformance gates | More work, but keeps student projects safe |

## Consequences

- Version 3 exposes an explicit native-runtime track rather than pretending
  the migration has already happened.
- Studio and CLI are designed around a process boundary, so the future engine
  can replace the reference executable without changing the user experience.
- The test suite is the contract: syntax and diagnostics must stay compatible.
