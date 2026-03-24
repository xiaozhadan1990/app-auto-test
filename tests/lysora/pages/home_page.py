from __future__ import annotations

from tests.lysora.pages.android.home_page import AndroidLysoraHomePage
from tests.lysora.pages.ios.home_page import IOSLysoraHomePage
from tests.lysora.pages.platform_factory import page_class_for


class LysoraHomePage:
    def __new__(cls, driver):
        impl = page_class_for(driver, AndroidLysoraHomePage, IOSLysoraHomePage)
        return impl(driver)
