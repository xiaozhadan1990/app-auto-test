from __future__ import annotations

import os

from tests.common.models import Account


def get_ruijie_cloud_accounts() -> list[Account]:
    return [
        Account("la_cloud", os.getenv("RUIJIECLOUD_ACCOUNT_LA", "xujianbin-la@yopmail.net"), os.getenv("RUIJIECLOUD_PASSWORD_LA", "xzd@1234")),
        Account("me_cloud", os.getenv("RUIJIECLOUD_ACCOUNT_ME", "xujianbin-me@yopmail.net"), os.getenv("RUIJIECLOUD_PASSWORD_ME", "Ruijie@123")),
        Account("a1_cloud", os.getenv("RUIJIECLOUD_ACCOUNT_A1", "xujianbin-a1@yopmail.net"), os.getenv("RUIJIECLOUD_PASSWORD_A1", "xzd@1234")),
        Account("ap_cloud", os.getenv("RUIJIECLOUD_ACCOUNT_AP", "xujianbin-ap@yopmail.net"), os.getenv("RUIJIECLOUD_PASSWORD_AP", "Ruijie@123")),
        Account("us_cloud", os.getenv("RUIJIECLOUD_ACCOUNT_US", "xujianbin-uk@yopmail.net"), os.getenv("RUIJIECLOUD_PASSWORD_US", "Ruijie@123")),
        Account("as_cloud", os.getenv("RUIJIECLOUD_ACCOUNT_AS", "xujianbin-as@yopmail.net"), os.getenv("RUIJIECLOUD_PASSWORD_AS", "Ruijie@123")),
        Account("uk_cloud", os.getenv("RUIJIECLOUD_ACCOUNT_UK", "xujianbin-uk@yopmail.net"), os.getenv("RUIJIECLOUD_PASSWORD_UK", "Ruijie@123")),
    ]


def get_smoke_account() -> Account:
    return next(account for account in get_ruijie_cloud_accounts() if account.name == "la_cloud")
