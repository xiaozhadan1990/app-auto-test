import os
import time
from typing import Iterable

import pytest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


LOGIN_EMAIL = "1003630917@qq.com"
LOGIN_PASSWORD = "Xjb5198565@"


def _first_clickable(driver, locators: Iterable[tuple[str, str]], timeout: int = 10):
    for by, value in locators:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            continue
    return None


def _first_visible(driver, locators: Iterable[tuple[str, str]], timeout: int = 10):
    for by, value in locators:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
        except TimeoutException:
            continue
    return None


def _click_if_exists(driver, locators: Iterable[tuple[str, str]], timeout: int = 8) -> bool:
    element = _first_clickable(driver, locators, timeout=timeout)
    if not element:
        return False
    element.click()
    return True


def _tap_bottom_my(driver) -> None:
    assert _click_if_exists(
        driver,
        [
            (
                AppiumBy.XPATH,
                "(//android.view.View[@content-desc='My' and @clickable='true'])[last()]",
            ),
            (
                AppiumBy.XPATH,
                "(//*[@text='My' and @clickable='true'])[last()]",
            ),
            (
                AppiumBy.XPATH,
                "(//android.widget.TextView[@text='My'])[last()]",
            ),
        ],
        timeout=10,
    ), "未找到底部 My tab"


def _open_register_login_entry(driver) -> None:
    assert _click_if_exists(
        driver,
        [
            (AppiumBy.ACCESSIBILITY_ID, "Register/Log In , Log in to learn more"),
            (
                AppiumBy.XPATH,
                "//*[contains(@content-desc,'Register/Log In') or contains(@text,'Register/Log In')]",
            ),
        ],
        timeout=10,
    ), "未找到 Register/Log In 入口"


def _is_account_visible_on_my_page(driver, timeout: int = 4) -> bool:
    return (
        _first_visible(
            driver,
            [
                (
                    AppiumBy.XPATH,
                    "//*[contains(@text,'1003630917@qq') or contains(@content-desc,'1003630917@qq')]",
                ),
                (AppiumBy.XPATH, "//*[contains(@text,'Join Lysora Cloud')]"),
            ],
            timeout=timeout,
        )
        is not None
    )


def _enter_email_and_blur(driver) -> None:
    email_input = _first_visible(
        driver,
        [
            (AppiumBy.XPATH, "(//android.widget.EditText)[1]"),
            (AppiumBy.XPATH, "//*[contains(@text,'Email')]"),
        ],
        timeout=10,
    )
    assert email_input is not None, "未找到 email 输入框"
    email_input.click()
    email_input.clear()
    email_input.send_keys(LOGIN_EMAIL)

    # 通过切换到密码框实现取消 email 输入框焦点。
    pwd_input = _first_clickable(
        driver,
        [
            (AppiumBy.XPATH, "(//android.widget.EditText)[2]"),
            (AppiumBy.XPATH, "//*[contains(@text,'password')]"),
        ],
        timeout=10,
    )
    assert pwd_input is not None, "未找到 password 输入框"
    pwd_input.click()


def _enter_password_and_blur(driver) -> None:
    pwd_input = _first_visible(
        driver,
        [
            (AppiumBy.XPATH, "(//android.widget.EditText)[2]"),
            (AppiumBy.XPATH, "//*[contains(@text,'password')]"),
        ],
        timeout=10,
    )
    assert pwd_input is not None, "未找到 password 输入框"
    pwd_input.click()
    pwd_input.clear()
    pwd_input.send_keys(LOGIN_PASSWORD)

    # 通过收起键盘/返回键取消密码输入框焦点。
    try:
        driver.hide_keyboard()
    except Exception:
        try:
            driver.press_keycode(4)
        except Exception:
            pass


def _click_login(driver) -> None:
    assert _click_if_exists(
        driver,
        [
            (AppiumBy.ACCESSIBILITY_ID, "Log in"),
            (AppiumBy.XPATH, "//*[@text='Log in' or @content-desc='Log in']"),
        ],
        timeout=10,
    ), "未找到登录按钮"


def _click_agree_if_present(driver) -> None:
    _click_if_exists(
        driver,
        [
            (
                AppiumBy.XPATH,
                "//*[@text='Agree' or @text='AGREE' or @text='Accept' or @text='I Agree' "
                "or @content-desc='Agree' or @content-desc='Accept']",
            )
        ],
        timeout=8,
    )


@pytest.mark.smoke
@pytest.mark.full
@pytest.mark.lysora
def test_lysora_login_and_verify_account_in_my_tab(driver):
    """按 8 步流程：登录 Lysora，并在 My 页断言账号存在。"""
    lysora_package = os.getenv("LYSORA_APP_PACKAGE", "com.lysora.lyapp")
    driver.activate_app(lysora_package)
    time.sleep(2)

    # 1~3
    _tap_bottom_my(driver)
    needs_login = not _is_account_visible_on_my_page(driver, timeout=4)
    if needs_login:
        _open_register_login_entry(driver)

    # 4~5
    if needs_login:
        _enter_email_and_blur(driver)
        _enter_password_and_blur(driver)

    # 6~7
    if needs_login:
        _click_login(driver)
        _click_agree_if_present(driver)

    # 8
    _tap_bottom_my(driver)
    account_info = _first_visible(
        driver,
        [
            (
                AppiumBy.XPATH,
                "//*[contains(@text,'1003630917@qq') or contains(@content-desc,'1003630917@qq')]",
            ),
            (AppiumBy.XPATH, "//*[contains(@text,'Join Lysora Cloud')]"),
        ],
        timeout=12,
    )
    assert account_info is not None, f"My 页面未检测到账号信息: {LOGIN_EMAIL}"
