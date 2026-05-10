"""Example shape of an operator-private pattern file.

This file is committed for documentation purposes. It contains placeholder
strings only. The real operator-private pattern file lives outside version
control and is referenced via the ``STYLE_LINT_PRIVATE_RULES`` environment
variable.

Shape contract:

- Module exposes a list named ``RULES``.
- Each element is a dict with the same keys as the entries in
  ``style_lint.py``'s ``PATTERNS`` list:
  ``severity``, ``rule``, ``pattern`` (compiled ``re``), ``preserve_if``
  (callable taking a line and returning a bool), ``message``.
- The ``re`` module is available in the loader's namespace.
"""
import re

RULES = [
    {
        "severity": "S4",
        "rule": "operator-real-name-firewall",
        "pattern": re.compile(r"\b(?:PLACEHOLDER_REAL_NAME_A|PLACEHOLDER_REAL_NAME_B)\b"),
        "preserve_if": lambda line: False,
        "message": (
            "Pseudonym firewall violation — the operator's real name must "
            "not appear in outbound material. (Public placeholder rule; "
            "real strings live outside version control.)"
        ),
    },
    {
        "severity": "S4",
        "rule": "internal-tooling-name-leak",
        "pattern": re.compile(r"\b(?:PLACEHOLDER_INTERNAL_SYSTEM_NAME)\b"),
        "preserve_if": lambda line: False,
        "message": (
            "Internal system name appears in outbound material. (Public "
            "placeholder rule; real strings live outside version control.)"
        ),
    },
]
