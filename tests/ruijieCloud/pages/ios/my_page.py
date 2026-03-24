from __future__ import annotations

from tests.ruijieCloud.pages.ios._base import IOSRuijieCloudPage


class IOSRuijieCloudMyPage(IOSRuijieCloudPage):
    feature_name = "RuijieCloud My page"

    def open(self) -> None:
        self._not_implemented()

    def open_login_entry(self) -> None:
        self._not_implemented()

    def assert_logged_in(self, email: str, screenshot_name: str) -> None:
        self._not_implemented()

    def logout(self) -> None:
        self._not_implemented()
