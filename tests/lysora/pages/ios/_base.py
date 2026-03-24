from __future__ import annotations

from tests.common.base_page import BasePage


class IOSLysoraPage(BasePage):
    feature_name = "Lysora iOS page"

    def _not_implemented(self) -> None:
        raise NotImplementedError(f"{self.feature_name} is not implemented yet for iOS")
