from __future__ import annotations

from tests.reyee.pages.ios._base import IOSReyeePage


class IOSReyeeMyPage(IOSReyeePage):
    feature_name = "Reyee My page"

    def open(self) -> None:
        self._not_implemented()

    def open_login_entry(self) -> None:
        self._not_implemented()

    def assert_account_visible(self, phone: str) -> None:
        self._not_implemented()
