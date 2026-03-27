from __future__ import annotations

from tests.reyee.pages.android.project_page import AndroidReyeeProjectPage
from tests.reyee.pages.ios.project_page import IOSReyeeProjectPage
from tests.reyee.pages.platform_factory import page_class_for


class ReyeeProjectPage:
    def __new__(cls, driver):
        impl = page_class_for(driver, AndroidReyeeProjectPage, IOSReyeeProjectPage)
        return impl(driver)
