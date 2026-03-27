from __future__ import annotations

from tests.lysora.pages.demo_experience_page import LysoraDemoExperiencePage


class LysoraDemoExperienceFlow:
    def __init__(self, driver):
        self.demo_page = LysoraDemoExperiencePage(driver)

    def run_create_demo_project_flow(self, app_id: str | None = None) -> None:
        if app_id:
            self.demo_page.activate_app(app_id, settle_seconds=0)
        self.demo_page.open_project_tab()
        self.demo_page.open_demo_experience()
        self.demo_page.open_smb_cctv_demo()
        self.demo_page.create_demo_project()
        self.demo_page.wait_and_assert_smb_project_exists(wait_seconds=10)
