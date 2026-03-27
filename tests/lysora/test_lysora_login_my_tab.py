import pytest

from tests.lysora.flows.login_flow import LysoraLoginFlow
from tests.lysora.pages.my_page import LysoraMyPage


@pytest.mark.smoke
@pytest.mark.full
@pytest.mark.lysora
@pytest.mark.case_name("Lysora 登录并校验 My 页账号")
@pytest.mark.case_priority(2)
def test_lysora_login_and_verify_account_in_my_tab(driver, lysora_app_id, lysora_account):
    my_page = LysoraMyPage(driver)
    my_page.activate_app(lysora_app_id)
    LysoraLoginFlow(driver).ensure_logged_in(lysora_account)
    my_page.open()
    my_page.assert_account_visible(lysora_account.username)
