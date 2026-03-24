from __future__ import annotations

from tests.ruijieCloud.pages.android.login_page import AndroidRuijieCloudLoginPage
from tests.ruijieCloud.pages.ios.login_page import IOSRuijieCloudLoginPage
from tests.ruijieCloud.pages.platform_factory import page_class_for


class RuijieCloudLoginPage:
    def __new__(cls, driver):
        impl = page_class_for(driver, AndroidRuijieCloudLoginPage, IOSRuijieCloudLoginPage)
        return impl(driver)
