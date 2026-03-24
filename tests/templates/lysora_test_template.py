import pytest

from tests.common.base_page import BasePage
from tests.templates.lysora_flow_template import LysoraFeatureFlow
from tests.templates.lysora_page_template import LysoraFeaturePage


@pytest.mark.smoke
@pytest.mark.lysora
@pytest.mark.case_name("Lysora 示例功能检查")
def test_lysora_feature_example(driver, lysora_app_id):
    BasePage(driver).activate_app(lysora_app_id)

    flow = LysoraFeatureFlow(driver)
    page = LysoraFeaturePage(driver)

    flow.run()
    page.assert_result_visible()
