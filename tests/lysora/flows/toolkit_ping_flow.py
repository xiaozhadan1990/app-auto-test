from __future__ import annotations

from tests.lysora.pages.ping_page import LysoraPingPage
from tests.lysora.pages.toolkit_page import LysoraToolkitPage


class LysoraToolkitPingFlow:
    def __init__(self, driver):
        self.toolkit_page = LysoraToolkitPage(driver)
        self.ping_page = LysoraPingPage(driver)

    def run_ping_and_end(self, host: str) -> None:
        self.toolkit_page.back_to_toolkit()
        self.toolkit_page.open()
        self.ping_page.open()
        self.ping_page.enter_host(host)
        self.ping_page.start_ping()
        self.ping_page.end_ping()
        self.ping_page.assert_result_actions_visible()

    def cleanup(self) -> None:
        self.toolkit_page.back_to_toolkit()
