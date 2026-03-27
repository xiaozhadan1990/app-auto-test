from __future__ import annotations

from tests.common.base_page import BasePage


class IOSReyeePage(BasePage):
    feature_name = "Reyee iOS page"

    def _not_implemented(self) -> None:
        raise NotImplementedError(f"{self.feature_name} is not implemented yet for iOS")
