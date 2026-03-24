from __future__ import annotations

from tests.ruijieCloud.pages.ios._base import IOSRuijieCloudPage


class IOSRuijieCloudLoginPage(IOSRuijieCloudPage):
    feature_name = "RuijieCloud login page"

    def enter_email(self, email: str) -> None:
        self._not_implemented()

    def enter_password(self, password: str) -> None:
        self._not_implemented()

    def agree_terms_if_present(self) -> None:
        self._not_implemented()

    def tap_login(self) -> None:
        self._not_implemented()

    def accept_dialogs_if_needed(self) -> None:
        self._not_implemented()
