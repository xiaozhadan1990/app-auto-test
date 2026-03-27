import pytest

from tests.reyee.data import get_reyee_default_account
from tests.reyee.flows.project_flow import ReyeeProjectFlow


@pytest.mark.smoke
@pytest.mark.reyee
@pytest.mark.case_priority(2)
@pytest.mark.case_name("Reyee 创建并删除通用场景虚拟项目")
def test_reyee_create_and_delete_common_scene_virtual_project(driver, reyee_app_id):
    account = get_reyee_default_account()
    ReyeeProjectFlow(driver).run_create_and_delete_common_scene_project(account, app_id=reyee_app_id)
