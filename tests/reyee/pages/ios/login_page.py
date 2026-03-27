from __future__ import annotations

from tests.reyee.pages.ios._base import IOSReyeePage


class IOSReyeeLoginPage(IOSReyeePage):
    feature_name = "Reyee Login page"

    def enter_phone(self, phone: str) -> None:
        self._not_implemented()

    def enter_password(self, password: str) -> None:
        self._not_implemented()

    def tap_login(self) -> None:
        self._not_implemented()

    def accept_user_agreement_if_present(self) -> None:
        self._not_implemented()
