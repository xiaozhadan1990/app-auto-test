from __future__ import annotations

import os

from tests.common.models import Account


def get_reyee_default_account() -> Account:
    return Account(
        name="reyee_default",
        username=os.getenv("REEYEE_TEST_PHONE", "15980631284"),
        password=os.getenv("REEYEE_TEST_PASSWORD", "admin1234"),
    )
