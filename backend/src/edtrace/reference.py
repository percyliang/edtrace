from dataclasses import dataclass

@dataclass(frozen=True)
class Reference:
    title: str | None = None
    authors: list[str] | None = None
    organization: str | None = None
    date: str | None = None
    url: str | None = None
    description: str | None = None
    notes: str | None = None


def join(*lines: list[str]) -> str:
    return "\n".join(lines)