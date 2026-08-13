---
description: Run the verification gate (engine import, GDScript parse, tests, manifest, licences, budgets)
argument-hint: "[project path — defaults to cwd] [--strict] [--no-engine]"
allowed-tools: Bash, Read
---

Run the gate:

```sh
"${STUDIO_CORE:-../studio-core}/scripts/verify.sh" $ARGUMENTS
```

Report the exit code and, on failure, the failing sections verbatim. Do not paraphrase engine
or checker output — the exact message is what makes the failure diagnosable.

**Do not start fixing.** This command reports; fixing is a builder task governed by the packet's
`attempts` field and the two-strike rule. If the caller wants a fix, that is `/next-task`.

If the failure is a missing tool rather than a defect — no Godot, no PyYAML, no test framework —
say so plainly and name the install step. That is an environment problem, not a code problem,
and burning attempts on it is waste.
