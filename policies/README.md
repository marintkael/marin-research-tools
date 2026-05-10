# Policies — operator-private pattern layer

`style_lint.py` carries the generic, public set of patterns: canon
contradictions, persona drift, encoding drift, Reddit / Hardcover
surface rules.

The author also runs an **operator-private** layer that catches things which
are by definition operator-specific:

- The author's real-name firewall (the pseudonym must not leak in either
  direction).
- Internal-system names that are part of the operator's local workflow but
  should never appear in outbound material.
- Project-private patterns (clients, contracts, draft material under
  embargo).

Those patterns are deliberately **not** committed to this repository.
Committing them would defeat the purpose — anyone reading the file would
learn the very strings the rule is supposed to suppress.

## How the framework loads them

`style_lint.py` reads an environment variable at startup:

```bash
export STYLE_LINT_PRIVATE_RULES=/path/to/private_rules.py
```

If the file exists and exposes a list named `RULES`, those entries are
appended to the public pattern set. The shape is identical to the public
patterns:

```python
import re

RULES = [
    {
        "severity": "S4",
        "rule": "operator-real-name-firewall",
        "pattern": re.compile(r"\b(?:placeholder_for_real_name)\b"),
        "preserve_if": lambda line: False,
        "message": "Real-name leak — operator pseudonym must not appear in outbound material.",
    },
    # ... more operator-private rules ...
]
```

See [`operator_patterns_example.py`](operator_patterns_example.py) for a
runnable shape (with placeholder strings only).

## Why this design

Three properties matter:

1. **Auditable framework.** Reviewers can read every public pattern and
   understand exactly what the linter does. Nothing functional is hidden.
2. **Private specifics.** The actual strings that the operator needs to
   suppress remain in a file that is not in version control and is loaded
   per machine.
3. **No special branch.** The public version and the operator-private
   version are the same `style_lint.py`. Only the `STYLE_LINT_PRIVATE_RULES`
   environment variable is different.
