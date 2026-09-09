# TajikLang 3.0

TajikLang 3 turns the language, Studio and learning tools into one project
platform. It does not remove version 2: the complete v2 installer remains on
the [GitHub Releases](https://github.com/BahromPython/tajiklang-2.0.0/releases)
page and every existing `.tj` program remains supported.

## Studio 3

- Open a project folder and browse its TajikLang, web and documentation files.
- Run or check the open program with one click (`F5` runs; **Санҷиш** checks).
- Keep an automatic local recovery copy while writing.
- Search inside the open program, switch to a calm light theme, and view the
  official package catalogue.
- Open `.tj` files directly from the operating system and use the same file
  from the terminal with `tajik my_program.tj`.

## Projects

```text
tajik init console номи_лоиҳа
tajik init web сомонаи_ман
tajik init game бозии_ман
tajik init blocks блокҳои_ман
tajik init data маълумоти_ман
```

Every template creates a project-local `.tajiklang/` environment, a runnable
`барнома.tj`, and a short README. Libraries stay with the project instead of
mixing with unrelated work.

## Web, blocks and libraries

- **TajikWeb** builds static sites and serves interactive pages locally.
- **TajikBlocks** saves, restores, reorders and runs visual programs, then
  shows their TajikLang code.
- Official packages already include `бозӣ`, `расм`, `ҷадвал`, `омор` and
  `шакл`; the package browser and `tajik ҷустуҷӯ` make them discoverable.
- The built-in `саҳифа` module provides headings, text, containers, rows,
  tables, buttons and styles for TajikWeb.

## Diagnostics

TajikLang checks a program before execution and returns line, column, source
pointer, an explanation and a suggested correction in Tajik. Studio sends the
same checker result to its **Хатоҳо** panel.

## Native-runtime migration

Students do not install Python: the desktop app remains a single installer.
The engine is moving to Rust as described in
[ADR-002](ADR-002-native-runtime.md). The tested reference runtime stays in
the package until the native runtime satisfies the same conformance tests;
this protects working student code during the migration.
