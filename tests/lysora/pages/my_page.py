from __future__ import annotations

from tests.lysora.pages.android.my_page import AndroidLysoraMyPage
from tests.lysora.pages.ios.my_page import IOSLysoraMyPage
from tests.lysora.pages.platform_factory import page_class_for


class LysoraMyPage:
    def __new__(cls, driver):
        impl = page_class_for(driver, AndroidLysoraMyPage, IOSLysoraMyPage)
        return impl(driver)
