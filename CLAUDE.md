# CLAUDE.md

## Project Overview

移动端自动化测试平台，集成 Python Flask 后端 + React 前端 + pytest/Appium 测试执行。
当前以 Android 自动化测试为主，架构已预留 iOS 适配能力。

支持两个被测应用：**Lysora** 和 **RuijieCloud**。

## Tech Stack

- **后端**: Python 3.11+ / Flask / waitress / SQLite
- **前端**: React 18 / TypeScript / Vite / Ant Design
- **测试**: pytest / Appium / allure-pytest
- **包管理**: uv (Python) / yarn (Node.js)
- **打包**: PyInstaller

## Quick Commands

```powershell
# 安装依赖
uv sync
cd web-ui && yarn install && cd ..

# 启动后端
uv run python .\desktop_web_app.py

# 启动前端开发
cd web-ui && yarn dev

# 一键启动/停止
.\start_dev_all.ps1
.\stop_dev_all.ps1

# 运行测试
uv run pytest tests/
uv run pytest tests/ -m smoke
uv run pytest tests/ -m "lysora and smoke"

# 构建前端
cd web-ui && yarn build

# 打包桌面版
.\build_web_ui.bat
```

## Project Structure

```
desktop_web_app.py          # Flask 应用入口
desktop_app/
  app_factory.py            # Flask app 创建
  services_container.py     # 服务组合/依赖注入
  api.py                    # REST API 路由
  task_service.py           # 任务执行管理
  report_service.py         # 报告服务
  db_service.py             # SQLite 数据访问
  device_service.py         # 设备管理 (adb)
  package_service.py        # 测试包管理
  remote_ws_service.py      # 远程 WebSocket 控制
conftest.py                 # pytest 配置和 fixtures
pytest.ini                  # pytest 配置
tests/
  lysora/                   # Lysora 测试用例
  ruijieCloud/              # RuijieCloud 测试用例
  common/                   # 公共测试工具 (BasePage, 平台检测, 报告)
web-ui/src/App.tsx          # 前端主组件（大量 UI 逻辑集中于此）
ui/                         # 构建后的前端静态文件（Flask 服务）
reports/                    # 运行时输出（DB, 日志, 报告, 截图, 视频）
```

## Key Architecture Rules

1. **入口保持轻量** — 业务逻辑放 service 模块，不要放 `desktop_web_app.py`
2. **路由保持精简** — `api.py` 只做请求解析和调用 service，不放业务编排
3. **双模式路径** — 必须同时支持源码运行和 PyInstaller 打包运行（注意 `RESOURCE_ROOT` / `RUNTIME_ROOT`）
4. **状态三处一致** — 内存状态、SQLite、前端轮询必须保持同步
5. **单设备单任务** — 同一设备不允许并发执行测试任务
6. **前后端契约** — 改 API 字段必须同步检查 `api.py` 和 `App.tsx`

## File Coupling (改一个要检查另一个)

| 改动区域 | 联动检查 |
|---------|---------|
| API 请求/响应字段 | `api.py`, `services_container.py`, 对应 service, `App.tsx` |
| 任务执行逻辑 | `task_service.py`, `services_container.py`, `conftest.py` |
| 报告结构/资源 URL | `report_service.py`, `db_service.py`, `App.tsx` |
| 设备状态/锁定 | `task_service.py`, `db_service.py`, `device_service.py`, `App.tsx` |
| 路径处理 | `desktop_web_app.py`, `services_container.py`, 报告资源解析 |

## Testing Conventions

- 按业务域组织：`tests/lysora/`, `tests/ruijieCloud/`
- Page Object 模式：`pages/android/`, `pages/ios/`, 顶层 `pages/*.py` 选择平台
- 常用 markers: `smoke`, `full`, `lysora`, `ruijieCloud`
- 自定义装饰器: `@case_name("用例名")` 设置报告展示名

## Environment

- 默认端口：后端 `17999`，前端开发 `5173`，Appium `4723`
- 环境变量模板：`.env.example`
- 关键环境变量：`APPIUM_SERVER_URL`, `APPIUM_UDID`, `DESKTOP_WEB_PORT`, `*_APP_PACKAGE`

## Code Style

- Python：遵循项目现有风格，中文注释
- 前端：TypeScript + Ant Design 组件
- 提交信息：中文描述

## Don'ts

- 不要假设这是纯前端或纯 pytest 项目
- 不要只考虑源码模式而忽略打包模式的路径
- 不要改 API 字段而不检查前端
- 不要改任务状态语义而不检查 DB 和 UI
- 不要在修小 bug 时顺带做无关重构
