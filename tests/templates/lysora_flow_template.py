from __future__ import annotations

from tests.templates.lysora_page_template import LysoraFeaturePage


class LysoraFeatureFlow:
    def __init__(self, driver):
        self.feature_page = LysoraFeaturePage(driver)

    def run(self) -> None:
        self.feature_page.open_feature()
