# TajikLang Native Runtime

This folder is the independent-runtime track for TajikLang 3. It exists so
the project has a clear boundary between the **language specification** and
the Python reference interpreter that made versions 0–2 possible.

## Status

The released 3.0 Studio still embeds the tested reference runtime so every
existing `.tj` program keeps working. It does **not** require a student to
install Python. The native runtime is intentionally not selected until it can
run the same conformance tests; claiming otherwise would make v3 less useful,
not more independent.

## Target architecture

```text
.tj source → Rust lexer → Rust parser → TajikLang AST → Rust evaluator
                                                    ↘ diagnostics JSON
```

Studio will invoke the evaluator through a small JSON command protocol. That
lets one runtime serve Windows, macOS and Linux without Electron knowing how
the language is implemented.

## Migration gates

1. Token and Unicode identifier parity.
2. TajikLang Next declarations, output and brace blocks.
3. Expressions, functions, lists and dictionaries.
4. Imports, official libraries and diagnostics.
5. Every language conformance test passes in both runtimes.
6. Electron switches its bundled engine from the reference runtime to the
   Rust binary.

This is a compatibility-first migration, not a rewrite that silently removes
features students already use.
