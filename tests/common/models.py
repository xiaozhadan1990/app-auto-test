from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    name: str
    username: str
    password: str
