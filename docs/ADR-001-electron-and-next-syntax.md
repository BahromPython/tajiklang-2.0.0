# ADR-001: Electron Studio and TajikLang Next syntax

**Status:** Accepted  
**Date:** 2026-09-09  
**Deciders:** TajikLang project owner

## Context

TajikLang Studio needs the polish, iconography, layout control, and
cross-platform packaging expected from a serious IDE. Tkinter was useful for a
first offline editor, but cannot deliver a comparable workbench. The language
also needs a syntax that does not imitate Python's `бигзор`, `навис(...)`,
colons, and indentation-sensitive blocks.

## Decision

TajikLang Studio will migrate to Electron. The renderer is a web workbench and
the Electron main process exposes only open, save, and run operations through a
secure preload bridge. The TajikLang interpreter remains a separately packaged
runtime during migration; students never install Python.

New projects use TajikLang Next syntax:

```tj
дода ном <- "Баҳром"
нишон "Салом", ном
агар ном != холӣ {
    нишон "Хуш омадед"
} дигар {
    нишон "Ном ворид кунед"
}
```

The previous syntax stays supported so existing lessons and projects do not
break.

## Options considered

### Continue with Tkinter

Low dependency cost, but limited typography, vector icon support, layout
control, and browser-quality editor interaction.

### Electron workbench

Higher packaged size and a Node build toolchain, but offers a professional
cross-platform IDE shell, secure native integration, CSS-level polish, and a
clear path to Monaco Editor and extensions.

### Rewrite the whole runtime before changing syntax

Would delay user-facing progress and make existing programs unstable. Runtime
replacement is a later, independent engineering milestone.

## Consequences

- Electron becomes the student-facing Studio shell.
- Existing Tkinter Studio remains as a temporary fallback until Electron is in
  every release pipeline.
- The language's external syntax can evolve independently of its current
  interpreter implementation.
- A future ADR must select a non-Python runtime implementation (Rust, Go, or
  C++) after the Next grammar is stable.

## Action items

1. Package the Electron shell with the platform runtime in CI.
2. Move execution diagnostics from CLI text into structured Electron output.
3. Add Next syntax for loops and functions after classroom testing.
4. Evaluate a Rust runtime once the grammar is frozen.
