from __future__ import annotations

from tests.common.models import Account
from tests.ruijieCloud.pages.login_page import RuijieCloudLoginPage
from tests.ruijieCloud.pages.my_page import RuijieCloudMyPage


class RuijieCloudLoginFlow:
    def __init__(self, driver):
        self.my_page = RuijieCloudMyPage(driver)
        self.login_page = RuijieCloudLoginPage(driver)

    def run_login_logout_cycle(self, account: Account, app_id: str | None = None) -> None:
        if app_id:
            self.my_page.activate_app(app_id, settle_seconds=0)
        self.login_page.accept_dialogs_if_needed()
        self.my_page.open()
        self.my_page.open_login_entry()
        self.login_page.enter_email(account.username)
        self.login_page.enter_password(account.password)
        self.login_page.agree_terms_if_present()
        self.login_page.tap_login()
        self.login_page.accept_dialogs_if_needed()
        self.my_page.open()
        self.my_page.assert_logged_in(account.username, f"{account.name}_login_status.png")
        self.my_page.logout()
