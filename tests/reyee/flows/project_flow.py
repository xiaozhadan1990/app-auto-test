from __future__ import annotations

from tests.common.models import Account
from tests.reyee.flows.login_flow import ReyeeLoginFlow
from tests.reyee.pages.project_page import ReyeeProjectPage


class ReyeeProjectFlow:
    def __init__(self, driver):
        self.driver = driver
        self.login_flow = ReyeeLoginFlow(driver)
        self.project_page = ReyeeProjectPage(driver)

    def run_create_and_delete_common_scene_project(self, account: Account, app_id: str | None = None) -> None:
        self.login_flow.run_login_and_verify_my_account(account, app_id=app_id)
        self.project_page.open_project_tab()
        self.project_page.open_virtual_experience()
        self.project_page.open_common_scene()
        self.project_page.create_virtual_project()
        self.project_page.assert_project_visible("通用场景")
        self.project_page.open_project_more_menu()
        self.project_page.click_delete_project()
        self.project_page.confirm_delete_project()
        self.project_page.assert_project_not_exists("通用场景")
