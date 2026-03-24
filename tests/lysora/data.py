from __future__ import annotations

import os

from tests.common.models import Account


def get_lysora_default_account() -> Account:
    return Account(
        name="default",
        username=os.getenv("LYSORA_TEST_EMAIL", "1003630917@qq.com"),
        password=os.getenv("LYSORA_TEST_PASSWORD", "Xjb5198565@"),
    )
