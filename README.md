# app-auto-test

Android 移动端自动化测试框架，支持命令行与桌面 Web UI（Flask）两种运行方式，集成 Allure 测试报告。

## 功能特性

- 基于 Appium + UiAutomator2 驱动 Android 设备
- 支持多 App 测试套件（Lysora、锐捷云）
- 自动捕获失败截图与全程录屏
- 生成 Allure HTML 测试报告
- 桌面 Web UI 启动器（Flask + 浏览器自动打开）
- 支持打包为独立可执行文件（PyInstaller）

## 目录结构

```
app-auto-test/
├── conftest.py                  # Pytest 全局 fixtures（驱动初始化、截图、录屏）
├── desktop_web_app.py           # 桌面 Web UI 启动入口（装配 + main）
├── desktop_app/                 # 桌面 Web UI 后端模块
│   ├── api.py                   # Flask 路由定义
│   ├── app_factory.py           # Flask app 创建
│   ├── services_container.py    # 服务依赖容器（统一装配）
│   ├── task_service.py          # 任务执行与状态管理
│   ├── report_service.py        # 报告处理与数据读取
│   ├── db_service.py            # SQLite 读写与历史查询
│   ├── remote_ws_service.py     # 远程 WebSocket 控制
│   ├── device_service.py        # 设备信息查询
│   └── package_service.py       # 用例包与 case_name 显示名解析
├── pytest.ini                   # Pytest 配置
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量模板
├── tests/
│   ├── lysora/                  # Lysora App 测试用例
│   └── ruijieCloud/             # 锐捷云 App 测试用例
├── ui/                          # React 构建产物（由 web-ui 构建输出）
├── web-ui/                      # React + Antd + TypeScript 前端源码
├── build-assets/
│   └── tools/
│       ├── adb/                 # 内置 ADB 工具
│       └── appium/              # 内置 Appium & Node.js
├── reports/
│   ├── allure-results/          # Allure 原始结果
│   ├── allure-html/             # 生成的 HTML 报告
│   ├── screenshots/             # 失败截图
│   └── videos/                  # 测试录屏
├── run_tests_and_allure.ps1     # 命令行测试运行脚本
├── start_desktop_ui.ps1         # 桌面 Web UI 启动脚本（含端口占用检查）
└── build_web_ui.bat             # PyInstaller 打包脚本
```

## 环境准备

### 前置要求

- Python 3.8+
- Android 设备（开启 USB 调试）或模拟器
- ADB（可使用 `build-assets/tools/adb/` 内置版本）
- Appium（可使用 `build-assets/tools/appium/` 内置版本）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

复制模板并填写实际参数：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
APPIUM_SERVER_URL=http://127.0.0.1:4723
APPIUM_AUTOMATION_NAME=UiAutomator2
APPIUM_DEVICE_NAME=Android Device
APPIUM_UDID=<设备 UDID，通过 adb devices 查看>

# 锐捷云
RUIJIECLOUD_APP_PACKAGE=cn.com.ruijie.cloudapp
RUIJIECLOUD_APP_ACTIVITY=<启动 Activity>

# Lysora
LYSORA_APP_PACKAGE=com.lysora.lyapp
```

## 运行测试

### 命令行方式

使用 PowerShell 脚本运行：

```powershell
# 运行全部冒烟测试
.\run_tests_and_allure.ps1 -Suite smoke

# 运行指定 App 的完整测试并自动打开报告
.\run_tests_and_allure.ps1 -Suite full -Component lysora -OpenReport

# 参数说明
# -Suite       smoke | full           测试套件类型
# -Component   all | lysora | ruijieCloud  指定 App 范围
# -OpenReport  生成后自动打开报告
# -ServeReport 启动本地 HTTP 服务预览报告
```

直接使用 pytest：

```bash
# 运行所有测试
pytest tests/

# 按标记过滤
pytest tests/ -m smoke
pytest tests/ -m "lysora and smoke"
pytest tests/ -m ruijieCloud
```

### 桌面 Web UI 方式

```powershell
# 推荐：启动前检查端口占用
.\start_desktop_ui.ps1
```

前端本地开发（React）：

```powershell
# 终端1：启动后端（入口文件会装配 desktop_app 模块）
python .\desktop_web_app.py

# 终端2：启动前端（通过 Vite 代理访问后端 /api）
cd .\web-ui
yarn dev
```

一键启动前后端（推荐）：

```powershell
# 自动清理端口冲突并分别拉起后端 + 前端
.\start_dev_all.ps1

# 已安装依赖时可跳过检查
.\start_dev_all.ps1 -NoInstall
```

一键停止前后端：

```powershell
.\stop_dev_all.ps1
```

## 测试标记

| 标记 | 说明 |
|------|------|
| `smoke` | 冒烟测试，快速验证核心功能 |
| `full` | 完整回归测试 |
| `lysora` | Lysora App 专属用例 |
| `ruijieCloud` | 锐捷云 App 专属用例 |

## 测试报告

测试完成后，Allure 报告保存在 `reports/allure-html/`，失败截图和录屏分别在 `reports/screenshots/` 和 `reports/videos/`。

手动生成报告：

```bash
allure generate reports/allure-results -o reports/allure-html --clean
allure open reports/allure-html
```

## 打包为可执行文件

```powershell
.\build_web_ui.bat
```

打包产物输出到 `dist/` 目录，内含 ADB、Appium 等工具，可在无开发环境的 Windows 机器上直接运行。

## 依赖说明

| 依赖 | 用途 |
|------|------|
| Appium-Python-Client | Appium WebDriver 客户端 |
| pytest | 测试框架 |
| selenium | WebDriver 基础库 |
| allure-pytest | Allure 报告插件 |
| Pillow | 截图图像分析 |
| Flask | 桌面 Web UI 服务 |
