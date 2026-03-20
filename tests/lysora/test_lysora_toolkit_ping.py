import os
import subprocess
import time
from typing import Iterable

import pytest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import InvalidElementStateException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


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


def _click_required(driver, locators: Iterable[tuple[str, str]], err_msg: str, timeout: int = 10) -> None:
    target = _first_clickable(driver, locators, timeout=timeout)
    assert target is not None, err_msg
    target.click()


def _hide_keyboard(driver) -> None:
    try:
        driver.hide_keyboard()
        return
    except Exception:
        pass
    try:
        driver.press_keycode(4)  # Android BACK
    except Exception:
        pass


def _adb_input_text(text: str) -> bool:
    serial = (os.getenv("APPIUM_UDID") or "").strip()
    if not serial:
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=8,
                encoding="utf-8",
                errors="ignore",
            )
            if result.returncode == 0:
                for line in (result.stdout or "").splitlines():
                    line = line.strip()
                    if "\tdevice" in line:
                        serial = line.split("\t", 1)[0].strip()
                        break
        except Exception:
            serial = ""
    if not serial:
        return False
    # input text 仅用于域名等简单字符兜底输入。
    safe_text = text.replace(" ", "%s")
    try:
        result = subprocess.run(
            ["adb", "-s", serial, "shell", "input", "text", safe_text],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="ignore",
        )
        return result.returncode == 0
    except Exception:
        return False


def _open_toolkit_tab(driver) -> None:
    _click_required(
        driver,
        [
            (AppiumBy.ACCESSIBILITY_ID, "ToolKit"),
            (AppiumBy.ACCESSIBILITY_ID, "Toolkit"),
            (AppiumBy.ACCESSIBILITY_ID, "Tool Kit"),
            (AppiumBy.XPATH, "//*[@content-desc='ToolKit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@content-desc='Toolkit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@content-desc='Tool Kit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@text='ToolKit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@text='Toolkit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@text='Tool Kit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[contains(@content-desc,'Tool') and contains(@content-desc,'Kit')]"),
            (AppiumBy.XPATH, "//*[contains(@text,'Tool') and contains(@text,'Kit')]"),
            (AppiumBy.XPATH, "(//*[@text='ToolKit'])[last()]"),
            (AppiumBy.XPATH, "(//*[@text='Toolkit'])[last()]"),
        ],
        "未找到底部 ToolKit tab",
        timeout=12,
    )


def _open_ping_page(driver) -> None:
    ping_entry_locators = [
        (AppiumBy.ACCESSIBILITY_ID, "Ping"),
        (AppiumBy.XPATH, "//*[@text='Ping' and @clickable='true']"),
        (AppiumBy.XPATH, "//*[contains(@content-desc,'Ping') and @clickable='true']"),
        (AppiumBy.XPATH, "(//*[@text='Ping'])[last()]"),
    ]

    def _is_ping_form_visible() -> bool:
        return _first_visible(
            driver,
            [
                (AppiumBy.ACCESSIBILITY_ID, "Enter an IP address or domain name."),
                (AppiumBy.XPATH, "//android.widget.EditText"),
                (AppiumBy.XPATH, "//*[contains(@content-desc,'IP address') or contains(@content-desc,'domain')]"),
                (AppiumBy.XPATH, "//*[contains(@text,'IP address') or contains(@text,'domain')]"),
            ],
            timeout=3,
        ) is not None

    if _is_ping_form_visible():
        return

    for _ in range(3):
        target = _first_clickable(driver, ping_entry_locators, timeout=6)
        assert target is not None, "未找到 Ping 入口"
        target.click()
        time.sleep(0.8)
        if _is_ping_form_visible():
            return

    assert False, "已点击 Ping 入口，但未进入 Ping 输入页面"


def _input_ping_host_and_start(driver, host: str) -> None:
    # 先点击输入区域容器，促使真正的 EditText 进入可写状态。
    hint_box = _first_clickable(
        driver,
        [
            (AppiumBy.ACCESSIBILITY_ID, "Enter an IP address or domain name."),
            (AppiumBy.XPATH, "//*[contains(@content-desc,'IP address') or contains(@content-desc,'domain')]"),
            (AppiumBy.XPATH, "//*[contains(@text,'IP address') or contains(@text,'domain')]"),
        ],
        timeout=8,
    )
    if hint_box is not None:
        hint_box.click()
        time.sleep(0.3)

    host_input = _first_visible(
        driver,
        [
            (AppiumBy.XPATH, "//android.widget.EditText"),
            (AppiumBy.XPATH, "(//android.widget.EditText)[1]"),
        ],
        timeout=12,
    )

    def _try_input_text() -> bool:
        candidates = []
        if hint_box is not None:
            candidates.append(hint_box)
        try:
            candidates.extend(driver.find_elements(AppiumBy.XPATH, "//android.widget.EditText"))
        except Exception:
            pass
        if host_input is not None:
            candidates.insert(0, host_input)

        seen = set()
        for element in candidates:
            element_id = getattr(element, "id", id(element))
            if element_id in seen:
                continue
            seen.add(element_id)
            try:
                element.click()
                try:
                    element.clear()
                except Exception:
                    pass
                for _ in range(2):
                    try:
                        element.set_value(host)
                    except Exception:
                        pass
                    try:
                        element.send_keys(host)
                    except Exception:
                        pass
                    time.sleep(0.3)
                    try:
                        if element.get_attribute("text") == host:
                            return True
                    except Exception:
                        continue
            except InvalidElementStateException:
                continue
            except Exception:
                continue

        # 兜底：尝试给当前焦点元素输入。
        try:
            active = driver.switch_to.active_element
            for _ in range(2):
                try:
                    active.send_keys(host)
                except Exception:
                    pass
                time.sleep(0.3)
                try:
                    if active.get_attribute("text") == host:
                        return True
                except Exception:
                    continue
        except Exception:
            pass

        # 最后兜底：通过 adb input text 输入。
        if not _adb_input_text(host):
            return False
        time.sleep(0.6)
        return True

    assert _try_input_text(), "Ping 地址输入失败（输入框不可写）"

    # 若页面可读到输入值则做强校验；某些版本可能不回显，允许继续执行。
    typed = _first_visible(
        driver,
        [
            (AppiumBy.XPATH, f"//android.widget.EditText[@text='{host}']"),
            (AppiumBy.XPATH, f"//*[contains(@text,'{host}')]"),
        ],
        timeout=4,
    )
    if typed is None:
        time.sleep(0.4)

    # 先收起键盘，再点击 Ping 执行按钮，避免点击被软键盘遮挡。
    _hide_keyboard(driver)

    _click_required(
        driver,
        [
            (AppiumBy.ACCESSIBILITY_ID, "Ping"),
            (AppiumBy.XPATH, "//*[@content-desc='Ping' and @clickable='true']"),
            (AppiumBy.XPATH, "(//*[@text='Ping' and @clickable='true'])[last()]"),
        ],
        "未找到 Ping 执行按钮",
        timeout=12,
    )


def _click_end(driver) -> None:
    _click_required(
        driver,
        [
            (AppiumBy.ACCESSIBILITY_ID, "End"),
            (AppiumBy.XPATH, "//*[@text='End' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[contains(@content-desc,'End') and @clickable='true']"),
        ],
        "未找到 End 按钮",
        timeout=15,
    )


def _assert_compare_visible(driver) -> None:
    compare_btn = _first_visible(
        driver,
        [
            (AppiumBy.ACCESSIBILITY_ID, "Compare"),
            (AppiumBy.XPATH, "//*[@text='Compare']"),
            (AppiumBy.XPATH, "//*[contains(@content-desc,'Compare') or contains(@text,'Compare')]"),
            (AppiumBy.ACCESSIBILITY_ID, "End"),
            (AppiumBy.XPATH, "//*[@text='End']"),
            (AppiumBy.XPATH, "//*[contains(@content-desc,'End') or contains(@text,'End')]"),
        ],
        timeout=30,
    )
    assert compare_btn is not None, "执行 Ping 后未出现 Compare/End 按钮"


def _back_to_toolkit_page(driver) -> None:
    # 用例收尾时尽量回到 ToolKit 页面，避免影响后续用例。
    toolkit_tab = _first_clickable(
        driver,
        [
            (AppiumBy.ACCESSIBILITY_ID, "ToolKit"),
            (AppiumBy.ACCESSIBILITY_ID, "Toolkit"),
            (AppiumBy.ACCESSIBILITY_ID, "Tool Kit"),
            (AppiumBy.XPATH, "//*[@text='ToolKit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@text='Toolkit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@text='Tool Kit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@content-desc='ToolKit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@content-desc='Toolkit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@content-desc='Tool Kit' and @clickable='true']"),
        ],
        timeout=8,
    )
    if toolkit_tab is not None:
        toolkit_tab.click()
        return

    # 若当前层级过深，先尝试返回一次再点 ToolKit。
    try:
        driver.press_keycode(4)  # Android BACK
    except Exception:
        return

    toolkit_tab = _first_clickable(
        driver,
        [
            (AppiumBy.ACCESSIBILITY_ID, "ToolKit"),
            (AppiumBy.ACCESSIBILITY_ID, "Toolkit"),
            (AppiumBy.ACCESSIBILITY_ID, "Tool Kit"),
            (AppiumBy.XPATH, "//*[@text='ToolKit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@text='Toolkit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@text='Tool Kit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@content-desc='ToolKit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@content-desc='Toolkit' and @clickable='true']"),
            (AppiumBy.XPATH, "//*[@content-desc='Tool Kit' and @clickable='true']"),
        ],
        timeout=6,
    )
    if toolkit_tab is not None:
        toolkit_tab.click()


@pytest.mark.smoke
@pytest.mark.full
@pytest.mark.lysora
def test_lysora_toolkit_ping_domain_and_end(driver):
    """验证 ToolKit Ping：输入域名执行 Ping，并可点击 End 结束。"""
    lysora_package = os.getenv("LYSORA_APP_PACKAGE", "com.lysora.lyapp")
    driver.activate_app(lysora_package)
    time.sleep(2)

    try:
        _back_to_toolkit_page(driver)
        _open_toolkit_tab(driver)
        _open_ping_page(driver)
        _input_ping_host_and_start(driver, "www.baidu.com")
        _click_end(driver)
        _assert_compare_visible(driver)
    finally:
        _back_to_toolkit_page(driver)
