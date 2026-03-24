from __future__ import annotations

from tests.lysora.pages.ios._base import IOSLysoraPage


class IOSLysoraPingPage(IOSLysoraPage):
    feature_name = "Lysora Ping page"

    def open(self) -> None:
        self._not_implemented()

    def is_form_visible(self) -> bool:
        self._not_implemented()
        return False

    def enter_host(self, host: str) -> None:
        self._not_implemented()

    def start_ping(self) -> None:
        self._not_implemented()

    def end_ping(self) -> None:
        self._not_implemented()

    def assert_result_actions_visible(self) -> None:
        self._not_implemented()
