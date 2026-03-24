# New Test Case Template

推荐按下面 5 步新增测试脚本：

1. 先在对应应用目录下补 `pages/`
2. 跨页面流程放到 `flows/`
3. 账号和测试数据放到 `data.py`
4. 测试文件只保留场景编排和断言
5. 优先通过 `conftest.py` 里的 fixture 获取包名、账号和 driver
6. 新增跨平台场景时，优先使用 `mobile_platform`、`lysora_app_id`、`ruijiecloud_app_id` 这类平台无关 fixture

最小结构示例：

```text
tests/
  your_app/
    pages/
      login_page.py
    flows/
      login_flow.py
    data.py
    test_login.py
```

测试文件可参考：

- `tests/templates/example_mobile_case.py`
- `tests/templates/lysora_page_template.py`
- `tests/templates/lysora_flow_template.py`
- `tests/templates/lysora_data_template.py`
- `tests/templates/lysora_test_template.py`
- `tests/lysora/test_lysora_login_my_tab.py`
- `tests/lysora/test_lysora_toolkit_ping.py`

Lysora 新增场景推荐复制方式：

1. 复制 `lysora_page_template.py` 到 `tests/lysora/pages/xxx_page.py`
2. 复制 `lysora_flow_template.py` 到 `tests/lysora/flows/xxx_flow.py`
3. 如果需要测试数据，复制 `lysora_data_template.py` 到 `tests/lysora/data_xxx.py`
4. 复制 `lysora_test_template.py` 到 `tests/lysora/test_xxx.py`

未来适配 iOS 时的建议：

1. 先复用现有 `flow` 和 `test`，仅在 `pages/` 中补 iOS locator
2. 应用标识统一使用 `*_app_id` fixture，不在测试文件里写死 Android package
3. 公共页面能力优先走 `BasePage` 的平台无关方法
4. 如需平台分支，优先根据 `mobile_platform` 在 page 或 flow 内部做最小判断
