import io
from typing import cast

import pytest
from PIL import Image

from tests.common.base_page import BasePage
from tests.lysora.pages.home_page import LysoraHomePage


def _assert_lysora_logo_rendered(page: BasePage) -> None:
    driver = page.driver
    png_bytes = driver.get_screenshot_as_png()
    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    width, height = image.size

    logo_roi = image.crop((0, int(height * 0.02), int(width * 0.45), int(height * 0.18)))
    dark_pixels = 0
    green_pixels = 0
    red_pixels = 0

    pixels = logo_roi.load()
    assert pixels is not None, "Unable to load screenshot pixels"
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
    assert dark_pixels > total_pixels * 0.01, "Lysora logo dark text feature not detected"
    assert green_pixels > 20, "Lysora logo green dot feature not detected"
    assert red_pixels > 5, "Lysora logo red dot feature not detected"

    screenshot_dir = page.extra_artifact_dir("screenshots", "lysora")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    image.save(screenshot_dir / "lysora_home_logo_check.png")


@pytest.mark.smoke
@pytest.mark.full
@pytest.mark.lysora
@pytest.mark.case_name("Lysora 首页 Logo 显示检查")
@pytest.mark.case_priority(1)
def test_lysora_home_has_logo(driver, lysora_app_id):
    page = BasePage(driver)
    page.activate_app(lysora_app_id)
    LysoraHomePage(driver).assert_loaded()
    _assert_lysora_logo_rendered(page)
