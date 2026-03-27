from __future__ import annotations

from tests.reyee.pages.android.my_page import AndroidReyeeMyPage
from tests.reyee.pages.ios.my_page import IOSReyeeMyPage
from tests.reyee.pages.platform_factory import page_class_for


class ReyeeMyPage:
    def __new__(cls, driver):
        impl = page_class_for(driver, AndroidReyeeMyPage, IOSReyeeMyPage)
        return impl(driver)
