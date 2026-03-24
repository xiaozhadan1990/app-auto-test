from __future__ import annotations

from tests.lysora.pages.android.toolkit_page import AndroidLysoraToolkitPage
from tests.lysora.pages.ios.toolkit_page import IOSLysoraToolkitPage
from tests.lysora.pages.platform_factory import page_class_for


class LysoraToolkitPage:
    def __new__(cls, driver):
        impl = page_class_for(driver, AndroidLysoraToolkitPage, IOSLysoraToolkitPage)
        return impl(driver)
