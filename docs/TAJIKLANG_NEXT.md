# TajikLang Next

TajikLang Next is the new practical syntax direction for TajikLang. It is
designed around explicit actions and braces, not Python's colons and invisible
indentation.

```tj
дода ном <- "Баҳром"
дода синну <- 16
нишон "Салом", ном

агар синну >= 16 {
    нишон "Хуш омадед"
} дигар {
    нишон "Идома диҳед"
}
```

| Purpose | Next syntax | Older syntax |
|---|---|---|
| introduce data | `дода ном <- "Баҳром"` | `бигзор ном = "Баҳром"` |
| update data | `тағйир ном <- "Далер"` | `ном = "Далер"` |
| show output | `нишон ном` | `навис(ном)` |
| conditional block | `агар шарт { ... }` | `агар шарт: ...` |
| alternative branch | `дигар { ... }` | `вагарна: ...` |

Both styles run today. New projects should use Next syntax; older lessons will
continue to work while the language migrates.

## Opening and running files

After the Windows installer finishes, double-click any `.tj` file to open it in
TajikLang Studio. You can also use a new Command Prompt or PowerShell window:

```text
tajik барнома.tj
```

The installer places the bundled runtime on your user PATH; Python is not
required.
