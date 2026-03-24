from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LysoraFeatureData:
    name: str
    expected_text: str


DEFAULT_LYSORA_FEATURE_DATA = LysoraFeatureData(
    name="default",
    expected_text="Expected Result",
)
