# app-auto-test

移动端自动化测试工具，包含两部分：

- Python 后端，用于设备管理、任务调度、测试执行和报告处理
- React 桌面 Web UI，用于在浏览器里操作测试任务和查看结果

当前项目以 Android 自动化测试为主，测试架构已经预留 iOS 适配能力。

## 功能概览

- 基于 Appium + pytest 执行移动端自动化测试
- 支持 `Lysora` 和 `RuijieCloud` 两个应用测试域
- 提供 Flask 桌面 Web UI
- 保存任务历史、日志、测试报告和截图/视频
- 支持 PyInstaller 打包桌面版运行程序

## 目录结构

```text
app-auto-test/
├── desktop_web_app.py
├── desktop_app/
├── tests/
├── web-ui/
├── ui/
├── reports/
├── conftest.py
├── pytest.ini
├── pyproject.toml
├── uv.lock
├── start_dev_all.ps1
├── stop_dev_all.ps1
├── run_tests_and_allure.ps1
└── build_web_ui.bat
```

## 环境要求

- `uv`
- Node.js
- yarn 或 npm
- Appium Server
- adb
- Android 设备或模拟器

如果后续运行 iOS 用例，还需要补充 iOS 对应的 Appium/XCUITest 环境。

## Python 依赖管理

项目现在使用 `uv` 管理 Python 依赖。

首次安装依赖：

```powershell
uv sync
```

常用运行方式：

```powershell
uv run python .\desktop_web_app.py
uv run pytest tests/
uv run pytest tests/ -m smoke
```

## 环境变量

先复制模板：

```powershell
Copy-Item .env.example .env
```

常用变量包括：

```env
APPIUM_SERVER_URL=http://127.0.0.1:4723
APPIUM_PLATFORM_NAME=android
APPIUM_AUTOMATION_NAME=UiAutomator2
APPIUM_DEVICE_NAME=Android Device
APPIUM_UDID=<device udid>

LYSORA_APP_PACKAGE=com.lysora.lyapp
RUIJIECLOUD_APP_PACKAGE=cn.com.ruijie.cloudapp
```

如果后续接入 iOS，可额外配置：

```env
APPIUM_PLATFORM_NAME=ios
LYSORA_IOS_BUNDLE_ID=<ios bundle id>
RUIJIECLOUD_IOS_BUNDLE_ID=<ios bundle id>
IOS_PLATFORM_VERSION=<ios version>
```

## 启动项目

### 启动后端

```powershell
uv run python .\desktop_web_app.py
```

### 启动前端开发服务

```powershell
cd .\web-ui
yarn dev
```

### 一键启动前后端

```powershell
.\start_dev_all.ps1
```

如果已经装好依赖，可跳过依赖同步：

```powershell
.\start_dev_all.ps1 -NoInstall
```

### 一键停止前后端

```powershell
.\stop_dev_all.ps1
```

## 运行测试

### 直接使用 pytest

```powershell
uv run pytest tests/
uv run pytest tests/ -m smoke
uv run pytest tests/ -m "lysora and smoke"
uv run pytest tests/ -m ruijieCloud
```

### 使用辅助脚本

```powershell
.\run_tests_and_allure.ps1 -Suite smoke
.\run_tests_and_allure.ps1 -Suite full -Component lysora
.\run_tests_and_allure.ps1 -Suite full -Component ruijieCloud -OpenReport
```

脚本参数：

- `-Suite smoke|full|all`
- `-Component all|lysora|ruijieCloud`
- `-GenerateReport`
- `-OpenReport`
- `-ServeReport`

说明：

- 测试执行走 `uv run pytest`
- 如果系统中存在 `allure` 命令，并传了报告参数，脚本会继续生成或打开 Allure 报告

## 测试标记

- `smoke`: 冒烟测试
- `full`: 全量回归测试
- `lysora`: Lysora 相关用例
- `ruijieCloud`: RuijieCloud 相关用例
- `case_name(name)`: 自定义中文用例显示名

## 测试报告

项目当前有两套报告输出：

### 1. 运行时 JSON / HTML 报告

生成位置：

- `reports/test_results.json`
- `reports/test_report.html`

特点：

- 由项目内置报告链路生成
- 已支持按 `app + platform` 区分截图、视频和测试结果

### 2. Allure 报告

默认目录：

- `reports/allure-results/`
- `reports/allure-html/`

手动生成：

```powershell
allure generate reports/allure-results -o reports/allure-html --clean
allure open reports/allure-html
```

## 打包桌面版

打包命令：

```powershell
uv sync
.\build_web_ui.bat
```

说明：

- 打包脚本已改成通过 `uv` 驱动 Python 依赖和 PyInstaller
- 前端仍通过 Node.js 构建
- 产物输出在 `dist/`
- 当前默认不再内置 `ADB / Appium / Node` 工具链
- 目标机器需要自己准备这些运行依赖

## 当前测试架构建议

项目测试代码推荐按业务域组织，而不是直接按平台拆顶层目录。

当前结构方向：

- `tests/lysora/`
- `tests/ruijieCloud/`
- `pages/android/`
- `pages/ios/`
- 顶层 `pages/*.py` 作为平台选择入口

建议原则：

- `test` 负责场景编排和断言
- `flow` 负责跨页面流程
- `page` 负责 locator 和页面动作
- 平台差异优先下沉到 `page`

## 说明

如果你在本地执行测试时报 `127.0.0.1:4723` 连接失败，通常表示：

- Appium Server 没有启动
- 设备没有连好
- `.env` 中的 Appium 地址配置不正确

这不是 `uv` 命令本身的问题，而是运行环境未就绪。
