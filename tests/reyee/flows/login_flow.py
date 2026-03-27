from __future__ import annotations

from tests.common.models import Account
from tests.reyee.pages.login_page import ReyeeLoginPage
from tests.reyee.pages.my_page import ReyeeMyPage


class ReyeeLoginFlow:
    def __init__(self, driver):
        self.login_page = ReyeeLoginPage(driver)
        self.my_page = ReyeeMyPage(driver)

    def run_login_and_verify_my_account(self, account: Account, app_id: str | None = None) -> None:
        if app_id:
            self.my_page.activate_app(app_id, settle_seconds=0)
        self.my_page.open()
        if self.my_page.is_account_visible(account.username):
            return
        self.my_page.open_login_entry()
        self.login_page.enter_phone(account.username)
        self.login_page.enter_password(account.password)
        self.login_page.tap_login()
        self.login_page.accept_user_agreement_if_present()
        self.my_page.open()
        self.my_page.assert_account_visible(account.username)
