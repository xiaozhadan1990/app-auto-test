from __future__ import annotations

from tests.lysora.pages.android.login_page import AndroidLysoraLoginPage
from tests.lysora.pages.ios.login_page import IOSLysoraLoginPage
from tests.lysora.pages.platform_factory import page_class_for


class LysoraLoginPage:
    def __new__(cls, driver):
        impl = page_class_for(driver, AndroidLysoraLoginPage, IOSLysoraLoginPage)
        return impl(driver)
