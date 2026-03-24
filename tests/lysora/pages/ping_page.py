from __future__ import annotations

from tests.lysora.pages.android.ping_page import AndroidLysoraPingPage
from tests.lysora.pages.ios.ping_page import IOSLysoraPingPage
from tests.lysora.pages.platform_factory import page_class_for


class LysoraPingPage:
    def __new__(cls, driver):
        impl = page_class_for(driver, AndroidLysoraPingPage, IOSLysoraPingPage)
        return impl(driver)
