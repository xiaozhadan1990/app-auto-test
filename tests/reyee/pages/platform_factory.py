from __future__ import annotations

from tests.common.mobile_platform import driver_platform_name


def page_class_for(driver, android_cls, ios_cls):
    if driver_platform_name(driver) == "ios":
        return ios_cls
    return android_cls
