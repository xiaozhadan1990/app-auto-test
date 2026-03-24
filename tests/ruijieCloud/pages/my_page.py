from __future__ import annotations

from tests.ruijieCloud.pages.android.my_page import AndroidRuijieCloudMyPage
from tests.ruijieCloud.pages.ios.my_page import IOSRuijieCloudMyPage
from tests.ruijieCloud.pages.platform_factory import page_class_for


class RuijieCloudMyPage:
    def __new__(cls, driver):
        impl = page_class_for(driver, AndroidRuijieCloudMyPage, IOSRuijieCloudMyPage)
        return impl(driver)
