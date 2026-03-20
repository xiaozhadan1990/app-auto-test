import io
import os
import time
from pathlib import Path
from typing import Iterable, cast

import pytest
from PIL import Image
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def _first_clickable(driver, locators: Iterable[tuple[str, str]], timeout: int = 8):
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


def _assert_home_loaded(driver) -> None:
    project_tab = _first_clickable(
        driver,
        [
            (
                AppiumBy.XPATH,
                "(//*[@text='Project' and @clickable='true'])[last()]",
            ),
            (
                AppiumBy.XPATH,
                "(//android.view.View[@content-desc='Project' and @clickable='true'])[last()]",
            ),
            (AppiumBy.XPATH, "(//android.widget.TextView[@text='Project'])[last()]"),
        ],
        timeout=5,
    )
    if project_tab is not None:
        project_tab.click()

    scan_entry = _first_visible(
        driver,
        [
            (AppiumBy.XPATH, '//*[@text="Scan"]'),
            (AppiumBy.XPATH, '//*[contains(@text, "Scan QR Code")]'),
            (AppiumBy.ACCESSIBILITY_ID, "Scan"),
        ],
        timeout=12,
    )
    assert scan_entry is not None, "未进入 Lysora 首页，未找到 Scan 区域"


def _assert_lysora_logo_rendered(driver) -> None:
    png_bytes = driver.get_screenshot_as_png()
    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    width, height = image.size

    # 左上角是 Lysora logo 所在区域，图片渲染时通常没有可定位文本属性。
    logo_roi = image.crop((0, int(height * 0.02), int(width * 0.45), int(height * 0.18)))
    dark_pixels = 0
    green_pixels = 0
    red_pixels = 0

    pixels = logo_roi.load()
    assert pixels is not None, "无法加载图像像素数据"
    roi_width, roi_height = logo_roi.size
    for y in range(roi_height):
        for x in range(roi_width):
            r, g, b = cast(tuple[int, int, int], pixels[x, y])
            if r < 80 and g < 80 and b < 80:
                dark_pixels += 1
            if g > 130 and r < 140 and b < 140:
                green_pixels += 1
            if r > 170 and g < 120 and b < 120:
                red_pixels += 1

    total_pixels = logo_roi.size[0] * logo_roi.size[1]
    assert dark_pixels > total_pixels * 0.01, (
        f"未检测到 Lysora logo 的深色主文字特征，dark_pixels={dark_pixels}"
    )
    assert green_pixels > 20, (
        f"未检测到 Lysora logo 的绿色点缀特征，green_pixels={green_pixels}"
    )
    assert red_pixels > 5, (
        f"未检测到 Lysora logo 的红色点缀特征，red_pixels={red_pixels}"
    )

    screenshot_dir = Path("reports/screenshots/lysora")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot = screenshot_dir / "lysora_home_logo_check.png"
    image.save(screenshot)


@pytest.mark.smoke
@pytest.mark.full
@pytest.mark.lysora
@pytest.mark.case_name("Lysora 首页 Logo 显示检查")
def test_lysora_home_has_logo(driver):
    """验证 Lysora 首页 logo 图片是否正确显示。"""
    lysora_package = os.getenv("LYSORA_APP_PACKAGE", "com.lysora.lyapp")
    driver.activate_app(lysora_package)
    time.sleep(2)

    _assert_home_loaded(driver)
    _assert_lysora_logo_rendered(driver)
