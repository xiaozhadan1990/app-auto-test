import pytest

from tests.common.base_page import BasePage
from tests.lysora.flows.toolkit_ping_flow import LysoraToolkitPingFlow


@pytest.mark.smoke
@pytest.mark.full
@pytest.mark.lysora
@pytest.mark.case_name("Lysora ToolKit Ping 域名执行与结束检查")
def test_lysora_toolkit_ping_domain_and_end(driver, lysora_app_id):
    BasePage(driver).activate_app(lysora_app_id)

    flow = LysoraToolkitPingFlow(driver)
    try:
        flow.run_ping_and_end("www.baidu.com")
    finally:
        flow.cleanup()
