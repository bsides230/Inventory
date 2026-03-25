from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class RecipientConfigError(ValueError):
    pass


@dataclass
class RecipientConfigStore:
    path: Path

    def __post_init__(self) -> None:
        self._cache: list[str] = []
        self._signature: tuple[int, int] | None = None

    def get_recipients(self) -> list[str]:
        if not self.path.exists():
            raise RecipientConfigError(f"Recipient config not found: {self.path}")

        stats = self.path.stat()
        signature = (stats.st_mtime_ns, stats.st_size)
        if self._signature is None or self._signature != signature:
            self._cache = parse_recipients_file(self.path)
            self._signature = signature
        return list(self._cache)


def parse_recipients_file(path: Path) -> list[str]:
    recipients: list[str] = []
    invalid_lines: list[str] = []

    for line_number, raw in enumerate(path.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not EMAIL_PATTERN.match(line):
            invalid_lines.append(f"line {line_number}: {line}")
            continue
        recipients.append(line.lower())

    if invalid_lines:
        raise RecipientConfigError("Invalid recipient emails: " + "; ".join(invalid_lines))
    if not recipients:
        raise RecipientConfigError("No valid recipients configured")

    # Preserve order but dedupe.
    seen: set[str] = set()
    deduped: list[str] = []
    for email in recipients:
        if email not in seen:
            deduped.append(email)
            seen.add(email)
    return deduped
