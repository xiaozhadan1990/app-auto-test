from __future__ import annotations

from tests.common.models import Account
from tests.lysora.pages.login_page import LysoraLoginPage
from tests.lysora.pages.my_page import LysoraMyPage


class LysoraLoginFlow:
    def __init__(self, driver):
        self.my_page = LysoraMyPage(driver)
        self.login_page = LysoraLoginPage(driver)

    def ensure_logged_in(self, account: Account) -> None:
        self.my_page.open()
        needs_login = not self.my_page.is_account_visible(account.username, timeout=4)
        if not needs_login:
            return
        self.my_page.open_login_entry()
        self.login_page.enter_email(account.username)
        self.login_page.enter_password(account.password)
        self.login_page.tap_login()
        self.login_page.accept_dialog_if_present()
