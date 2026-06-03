# Portability Contract

## Principle

The `martin-outcome-package/` skill folder must be **self-contained and portable**. It can be copied to any repo or vault and function without modification to the core runtime logic.

## Mandatory Rules

1. **No absolute local paths** in SKILL.md or references/ files. Paths like `/absolute/local/path/...` are forbidden in runtime instructions.
2. **No vault-specific paths** in runtime logic. Paths like `80 Blueprint/...`, `Daily/...`, `tasks/sessions/...` belong only in optional adapter docs or in `examples/`.
3. **No external tool dependencies** that are not standard agent capabilities. The Skill must not require Stitch, Taste, brand-style folders, or slash commands to function.
4. **Templates are self-contained**. Every template in `templates/` must work without external file references.
5. **References are internal**. Every file in `references/` references only other files within this Skill folder.

## Allowed Exceptions

- **Design-time examples** in `examples/` may reference Work-PKM paths to illustrate integration patterns.
- **Optional adapter pointer**: SKILL.md may mention that a vault-specific adapter exists, but must not require it.
- **Downstream skill references**: SKILL.md may reference `martin-pptx-skill` by name as a delegation target, since skill names are portable identifiers.

## Verification

Run this scan on all files in the Skill folder (excluding `examples/`):

```bash
grep -rn '/absolute/local/path' skills/martin-outcome-package/ --exclude-dir=examples
grep -rn '80 Blueprint/' skills/martin-outcome-package/ --exclude-dir=examples
grep -rn 'Daily/' skills/martin-outcome-package/ --exclude-dir=examples
grep -rn 'tasks/sessions/' skills/martin-outcome-package/ --exclude-dir=examples
```

All results must be zero or documented as false positives (e.g., in portability notes).
