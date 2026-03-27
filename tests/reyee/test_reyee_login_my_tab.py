import pytest

from tests.reyee.data import get_reyee_default_account
from tests.reyee.flows.login_flow import ReyeeLoginFlow


@pytest.mark.smoke
@pytest.mark.reyee
@pytest.mark.case_name("Reyee 登录并校验我的页账号")
def test_reyee_login_and_verify_account_in_my_tab(driver, reyee_app_id):
    account = get_reyee_default_account()
    ReyeeLoginFlow(driver).run_login_and_verify_my_account(account, app_id=reyee_app_id)
