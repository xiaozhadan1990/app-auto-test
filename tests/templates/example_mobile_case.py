import pytest

from tests.common.base_page import BasePage


@pytest.mark.smoke
@pytest.mark.case_name("示例：新移动端用例模板")
def test_example_mobile_case(driver, mobile_platform):
    page = BasePage(driver)

    # 1. 准备应用状态
    # page.activate_app("android.package.or.ios.bundle.id")
    # print(mobile_platform)

    # 2. 执行动作
    # flow = YourBusinessFlow(driver)
    # flow.run(...)

    # 3. 断言结果
    assert page.driver is not None
