# app-auto-test

移动端自动化测试工具，包含 Python 后端、桌面 Web UI、Airtest 执行链路，以及报告生成与查看能力。

当前项目以 Android 自动化测试为主，测试架构已经预留 iOS 适配能力。

## 功能概览

- 使用 Airtest 执行移动端自动化测试
- 支持扫描外部 Airtest 脚本目录并按设备执行
- 提供桌面 Web UI 管理设备、任务和报告
- 保存任务历史、日志、截图、视频和测试报告
- 支持 PyInstaller 打包桌面版运行程序
- 支持远程 WebSocket 控制与报告资产上传

## 目录结构

```text
app-auto-test/
├─ desktop_web_app.py
├─ desktop_app/
├─ tests/
├─ web-ui/
├─ ui/
├─ reports/
├─ conftest.py
├─ pyproject.toml
├─ uv.lock
├─ start_dev_all.ps1
├─ stop_dev_all.ps1
├─ scripts/
└─ build_web_ui.bat
```

## 环境要求

- `uv`
- Node.js
- yarn
- airtest 命令行工具
- adb
- Android 设备或模拟器

如果后续执行 iOS 用例，还需要补齐 iOS 真机连接与 Airtest 对应环境。

## Python 依赖管理

项目现在使用 `uv` 管理 Python 依赖。

首次安装依赖：

```powershell
uv sync
```

常用运行方式：

```powershell
uv run python .\desktop_web_app.py
uv run python .\scripts\run_airtest.py --platform android --device emulator-5554 --list
```

## 环境变量

先复制模板：

```powershell
Copy-Item .env.example .env
```

常用变量包括：

```env
AIRTEST_CASE_ROOT=/Users/ruijie/Documents/workspace/airProject/海外用例_wln
AIRTEST_BIN=airtest
```

如果后续接入 iOS，可额外指定平台和设备：

```env
AIRTEST_PLATFORM=ios
AIRTEST_DEVICE=<ios udid>
```

## 启动项目

### 启动后端

```powershell
uv run python .\desktop_web_app.py
```

说明：

- 启动入口会优先使用 `waitress` 作为 WSGI server
- 如果本地环境里没有 `waitress`，才会回退到 Flask 开发服务器

### 启动前端开发服务

```powershell
cd .\web-ui
yarn dev
```

### 一键启动前后端

```powershell
.\start_dev_all.ps1
```

说明：

- 脚本会先检查并同步 Python 依赖
- 如果 `web-ui/node_modules` 不存在，会自动执行 `yarn install`
- 后端通过 `uv run python desktop_web_app.py` 启动，默认优先使用 `waitress`

如果依赖已经准备好，可以跳过安装：

```powershell
.\start_dev_all.ps1 -NoInstall
```

### 一键停止前后端

```powershell
.\stop_dev_all.ps1
```

该脚本会停止默认后端端口 `17999` 和前端端口 `5173/5174` 上的监听进程。

## 运行测试

### 使用 Airtest 指定设备和指定用例

项目当前默认扫描外部目录：

```text
/Users/ruijie/Documents/workspace/airProject/海外用例_wln
```

如果你已经在本机单独装好了 `airtest` 命令行工具，可以直接使用项目内脚本入口：

```powershell
uv run python .\scripts\run_airtest.py --platform android --device emulator-5554 --list
uv run python .\scripts\run_airtest.py --platform android --device emulator-5554 --case 登录-切换tab-创建虚拟项目-进入项目加载正常.air
uv run python .\scripts\run_airtest.py --platform android --device emulator-5554 --case 登录-切换tab-创建虚拟项目-进入项目加载正常.air --case 五个tab页面切换测试.air
```

说明：

- `--device` 用来指定设备序列号或 iOS UDID
- `--case` 可重复传入多个 `.air` 用例目录
- 默认会扫描 `AIRTEST_CASE_ROOT` 指向的目录
- 日志默认输出到 `reports/airtest/`
- 如需特殊连接串，可通过 `--device-uri` 覆盖默认生成值

## 测试报告

项目当前的 Airtest 执行会生成一套运行时 JSON / HTML 报告。

### 1. 运行时 JSON / HTML 报告

生成位置：

- `reports/test_results.json`
- `reports/test_report.html`
- `reports/task-reports/<task_id>/`

特点：

- 桌面端会为每次任务生成汇总 HTML 报告
- 每个 Airtest 脚本会生成自己的独立 HTML 报告
- 报告中的资源统一通过后端接口访问

## 打包桌面版

打包命令：

```powershell
uv sync
.\build_web_ui.bat
```

说明：

- 打包脚本已改成通过 `uv` 驱动 Python 依赖和 PyInstaller
- 前端仍通过 Node.js 构建
- 产物输出到 `dist/`
- 当前默认不再内置 `ADB / airtest / Node` 工具链
- 目标机器需要自行准备这些运行依赖

## 当前测试架构建议

项目测试代码建议按业务域组织，而不是直接按平台拆顶层目录。

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

## 常见问题

如果桌面端没有扫到脚本或执行失败，通常优先检查：

- `AIRTEST_CASE_ROOT` 是否指向 `/Users/ruijie/Documents/workspace/airProject/海外用例_wln`
- `airtest` 命令是否可直接在终端执行
- 设备是否已通过 `adb devices` 或 iOS 真机链路正常连接
- `.env` 中的 Airtest 路径配置不正确

这不是 `uv` 本身的问题，而是运行环境尚未就绪。
