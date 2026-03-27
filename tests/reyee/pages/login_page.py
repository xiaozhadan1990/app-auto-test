from __future__ import annotations

from tests.reyee.pages.android.login_page import AndroidReyeeLoginPage
from tests.reyee.pages.ios.login_page import IOSReyeeLoginPage
from tests.reyee.pages.platform_factory import page_class_for


class ReyeeLoginPage:
    def __new__(cls, driver):
        impl = page_class_for(driver, AndroidReyeeLoginPage, IOSReyeeLoginPage)
        return impl(driver)
