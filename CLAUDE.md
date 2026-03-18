# CLAUDE.md

本文件用于指导 Claude Code（claude.ai/code）在本仓库内的协作方式、测试运行方式与关键架构认知。

## 项目概览

这是一个基于 Appium + UiAutomator2 + pytest 的 Android 自动化测试项目，支持两款应用：

- `Lysora`
- `RuijieCloud`

支持两种执行模式：

- 命令行（CLI）
- 桌面 Web UI（Flask）

测试运行目标为通过 ADB 连接的 Android 真机。

## 常用命令

### 通过 PowerShell 运行测试

```powershell
# 运行 smoke 套件
.\run_tests_and_allure.ps1 -Suite smoke

# 运行指定组件 full 回归并打开报告
.\run_tests_and_allure.ps1 -Suite full -Component lysora -OpenReport

# 直接使用 pytest（需自行先启动 Appium）
pytest tests/ -m smoke
pytest tests/ -m "lysora and smoke"
pytest tests/ -m ruijieCloud
pytest tests/lysora/test_lysora_home_logo.py -v  # 单文件运行
```

### 运行单条测试

```bash
pytest tests/lysora/test_lysora_login_my_tab.py::test_lysora_login_and_verify_account_in_my_tab -v
```

### 启动桌面 Web UI

```powershell
.\run_desktop_ui.ps1
```

### 打包桌面程序

```powershell
.\package_desktop_ui.ps1
```

## 架构说明

### 测试基础设施（`conftest.py`）

- 使用 session 级别的 Appium `driver` fixture，供全局测试复用。
- 从 `.env` 读取设备与服务配置（可由 `.env.example` 复制）。
- `record_test_video` 自动录制每条测试视频，输出至 `reports/videos/`。
- `pytest_runtest_makereport` 在失败时截图到 `reports/screenshots/{app}/`，并将截图与视频附加到 Allure。

### 桌面 Web UI（`desktop_web_app.py`）

后端为 Flask，前端页面为 `ui/desktop_app.html`，主要能力：

- 启动时自动打开浏览器。
- 不在 UI 内管理 Appium 生命周期（需外部先启动/停止 Appium）。
- 枚举 ADB 设备与已安装应用版本。
- 启动 pytest 子进程前动态设置 `APPIUM_UDID`。
- 测试后生成并打开 Allure HTML 报告。

## 测试目录与标记

### 测试目录

- `tests/lysora/`：Lysora 相关用例（主页 logo 像素分析、登录/账号校验等）
- `tests/ruijieCloud/`：RuijieCloud 相关用例（7 个区域账号参数化登录/登出）

### Pytest Markers

| Marker | 说明 |
|--------|------|
| `smoke` | 核心冒烟测试 |
| `full` | 全量回归测试 |
| `lysora` | Lysora 专属用例 |
| `ruijieCloud` | RuijieCloud 专属用例 |

## 报告产物

- Allure 原始结果：`reports/allure-results/`
- Allure HTML 报告：`reports/allure-html/`

`run_tests_and_allure.ps1` 脚本会自动处理 `allure generate` 与 `allure open`。

## 环境配置

从 `.env.example` 复制 `.env`，并至少配置：

- `APPIUM_SERVER_URL`（默认 `http://127.0.0.1:4723`）
- `APPIUM_UDID`（ADB 设备序列号；留空时自动选择首个设备）
- 各应用 package 名称

内置工具位于 `build-assets/tools/`：

- ADB：`tools/adb/`
- Appium + Node.js：`tools/appium/`

说明：

- 桌面 UI 优先使用仓库内置工具路径。
- CLI 模式通常依赖系统环境中的 ADB/Appium。

## 测试代码模式

各测试文件通常使用两个 XPath 兜底辅助方法：

- `_first_clickable(driver, selectors, timeout)`：等待 selectors 中任一元素可点击
- `_first_visible(driver, selectors, timeout)`：等待 selectors 中任一元素可见

定位策略通常按优先级尝试（优先 accessibility id，再 XPath 兜底）以兼容不同版本 UI。

## 协作约定（给 AI/开发者）

- 优先最小改动：仅修改与当前需求直接相关的文件与逻辑。
- 保持测试可运行：改动测试基础设施后，至少验证一个 smoke 路径。
- 变更可追踪：新增脚本或配置时，同步更新本文档对应章节。
- 不在未经确认的情况下修改设备端环境（如覆盖 `.env`、重置设备状态）。
