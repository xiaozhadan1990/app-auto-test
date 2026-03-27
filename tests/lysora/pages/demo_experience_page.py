from __future__ import annotations

from tests.lysora.pages.android.demo_experience_page import AndroidLysoraDemoExperiencePage
from tests.lysora.pages.ios.demo_experience_page import IOSLysoraDemoExperiencePage
from tests.lysora.pages.platform_factory import page_class_for


class LysoraDemoExperiencePage:
    def __new__(cls, driver):
        impl = page_class_for(driver, AndroidLysoraDemoExperiencePage, IOSLysoraDemoExperiencePage)
        return impl(driver)
