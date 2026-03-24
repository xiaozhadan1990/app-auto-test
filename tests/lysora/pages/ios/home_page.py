from __future__ import annotations

from tests.lysora.pages.ios._base import IOSLysoraPage


class IOSLysoraHomePage(IOSLysoraPage):
    feature_name = "Lysora home page"

    def assert_loaded(self) -> None:
        self._not_implemented()
