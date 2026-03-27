import pytest

from tests.ruijieCloud.flows.login_flow import RuijieCloudLoginFlow


@pytest.mark.smoke
@pytest.mark.ruijieCloud
@pytest.mark.case_name("RuijieCloud 跨云账号登录登出（冒烟）")
@pytest.mark.case_priority(10)
def test_ruijie_cloud_login_logout_cycle_smoke(driver, ruijiecloud_app_id, ruijiecloud_smoke_account):
    RuijieCloudLoginFlow(driver).run_login_logout_cycle(
        ruijiecloud_smoke_account,
        app_id=ruijiecloud_app_id,
    )


@pytest.mark.full
@pytest.mark.ruijieCloud
@pytest.mark.case_name("RuijieCloud 跨云账号登录登出（全量）")
@pytest.mark.case_priority(20)
def test_ruijie_cloud_login_logout_cycle(driver, ruijiecloud_app_id, ruijiecloud_accounts):
    flow = RuijieCloudLoginFlow(driver)
    for account in ruijiecloud_accounts:
        flow.run_login_logout_cycle(account, app_id=ruijiecloud_app_id)
