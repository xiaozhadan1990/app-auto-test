# desktop_web_app.py 执行过程说明

本文档说明 `desktop_web_app.py` 的实际运行链路，按“启动 -> API 调用 -> 测试任务 -> 报告 -> 远程控制”展开。

## 1. 程序角色与职责

- 提供 Flask Web 服务，承载桌面端前端页面与 API。
- 调用 `adb` 获取设备信息。
- 调用 `pytest` 执行自动化测试（子进程）。
- 生成并管理测试报告（HTML + JSON + SQLite）。
- 可选连接远程 WebSocket，实现远程控制与状态上报。

## 2. 启动阶段（main）

入口函数：`main()`（`desktop_web_app.py`）

启动顺序：
1. 模块加载时先执行 `_load_local_env_file()`，从多个候选路径读取 `.env` 并写入环境变量（不覆盖已有变量）。
2. 进入 `main()` 后，先判断是否为 pytest 子进程模式：
   - 若命令行为 `--run-pytest`，直接 `pytest.main(...)` 后退出。
3. 正常服务模式下执行：
   - `_init_runtime_db()`：初始化 SQLite 表结构。
   - `_start_remote_ws_if_needed()`：若配置开启远程 WS，则启动后台线程连接。
   - 读取监听地址和端口（`DESKTOP_WEB_HOST` / `DESKTOP_WEB_PORT`）。
   - 如果启用 `DESKTOP_WEB_AUTO_PORT_FALLBACK`，调用 `_get_free_port(...)` 自动避让端口占用。
   - 启动后台线程 `_auto_open_browser(url)` 自动打开浏览器。
   - `app.run(...)` 启动 Flask 服务。

## 3. 全局状态与数据存储

### 3.1 内存状态

- `_tasks`: 运行中任务字典，按 `task_id` 存储子进程、状态、日志路径等。
- `_device_running_task`: 设备与任务映射，用于“一台设备同一时间仅允许一个任务”。
- `_tasks_lock`: 并发读写锁。

### 3.2 持久化状态（SQLite）

数据库文件：`reports/runtime_state.db`

关键表：
- `device_runtime_status`: 设备实时状态（idle/running/failed 等）。
- `task_run_history`: 任务历史（开始/结束时间、退出码、错误、日志路径）。
- `task_report_summary`: 报告汇总（总数、通过率、耗时等）。
- `task_report_cases`: 用例明细（状态、截图、视频、报错等）。

## 4. HTTP 路由与核心函数映射

### 4.1 页面与静态资源

- `GET /` -> `index()` -> 返回 `ui/index.html`
- `GET /assets/<path>` -> `ui_assets()` -> 返回前端静态资源

### 4.2 设备与配置

- `POST /api/list_devices` -> `_list_devices()`
  - 执行 `adb devices`
  - 对在线设备补充品牌/型号/系统版本
  - 查询 `APP_CONFIG` 中各 App 包名版本
- `GET /api/get_app_options` -> 读取 `APP_CONFIG`
- `POST /api/list_test_packages` -> `_list_test_packages(app_key)`

### 4.3 测试任务

- `POST /api/run_tests` -> `_run_tests(payload)`
- `GET /api/task_status/<task_id>` -> `_task_status(task_id)`
- `POST /api/stop_task` -> `_stop_task(payload)`
- `GET /api/task_history` -> `_get_task_history(...)`
- `GET /api/device_status/<device_serial>` -> `_get_device_status(...)`

### 4.4 报告与日志

- `GET /api/task_log/<task_id>` -> 下载任务日志
- `GET /api/task_report/<task_id>` -> 返回任务 HTML 报告
- `GET /api/task_report_data/<task_id>` -> `_get_task_report_data(...)`
- `GET /api/report_asset?path=...` -> 安全校验后返回截图/视频文件
- `POST /api/open_report` -> `_open_report()` 打开最新报告

### 4.5 启动检查与远程状态

- `GET /api/startup_info` -> `_startup_info()`（当前主要检查 `adb`）
- `GET /api/appium_ready` -> `_appium_ready()`（探测 `APPIUM_SERVER_URL/status`）
- `GET /api/remote_ws_status` -> `_remote_ws_status()`
- `GET /api/remote_ws_log` -> `_read_remote_ws_log_lines(...)`

## 5. 任务执行主流程（_run_tests）

`_run_tests(payload)` 核心链路：

1. 参数校验：
   - `device` 必填
   - `test_packages`（或 `test_package`）必填
2. 前置依赖校验：
   - 调用 `_appium_ready()`，未就绪则直接返回错误。
3. 组装 pytest 参数：
   - 默认 `-v`
   - `suite` 为 `smoke/full` 时添加 marker（可带 app_key 组合）。
4. 组装执行命令：
   - 打包模式：`sys.executable --run-pytest ...`
   - 开发模式：`sys.executable -m pytest ...`
5. 并发控制：
   - 检查 `_device_running_task`，同设备已有任务则拒绝。
6. 准备输出路径：
   - `reports/task-logs/<task_id>.log`
   - `reports/task-reports/<task_id>/test_results.json`
   - `reports/task-reports/<task_id>/test_report.html`
7. 构建子进程环境变量：
   - `APPIUM_UDID`
   - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`
   - `TEST_RESULTS_FILE` / `TEST_REPORT_FILE`（任务隔离）
8. `subprocess.Popen(...)` 启动 pytest 子进程。
9. 更新状态：
   - 内存 `_tasks` / `_device_running_task`
   - DB `task_run_history`（running）
   - DB `device_runtime_status`（running）
10. 启动后台监控线程 `_watch_task()`：
   - 持续读取 stdout 写日志文件。
   - 进程结束后生成/复制报告、写入报告数据到 DB。
   - 计算最终状态 success/failed/stopped 并同步到内存和 DB。

## 6. 报告处理流程

任务结束后 `_watch_task()` 进行后处理：

1. 若任务 HTML 报告不存在，调用 `report_generator.generate_report(...)` 尝试生成。
2. 将本任务报告复制为“最新报告”：
   - `reports/test_report.html`
   - `reports/test_results.json`
3. `_save_task_report_to_db(task_id, results_file)`：
   - 解析 JSON
   - 写 `task_report_summary` 与 `task_report_cases`
4. 若配置了 `REMOTE_REPORT_UPLOAD_URL`：
   - `_rewrite_report_assets_for_remote(...)` 尝试上传截图/视频
   - 将本地相对路径替换为远程 URL（若上传成功）

## 7. 远程 WebSocket 流程（可选）

是否启用：
- `_remote_ws_enabled()` 要求 `REMOTE_WS_URL` 非空，且 `REMOTE_WS_ENABLED` 未显式禁用。

运行机制：
1. `_start_remote_ws_if_needed()` 启动线程 `_remote_ws_runner()`。
2. `_remote_ws_runner()` 建立连接并注册客户端（`type=register`）。
3. 心跳线程 `_remote_ws_heartbeat_loop(...)` 周期发送 `type=heartbeat`。
4. 收到消息后 `_remote_ws_handle_message(raw)`：
   - 解析 `type=command`
   - 调用 `_remote_ws_exec_command(action, payload)`
   - 回传 `type=response`
5. 支持远程动作包括：
   - `list_devices` / `list_test_packages`
   - `run_tests` / `stop_task`
   - `task_status` / `task_report_data` / `task_history`
   - `device_status` / `startup_info` / `appium_ready`

## 8. 关键环境变量速览

- 服务监听：
  - `DESKTOP_WEB_HOST`
  - `DESKTOP_WEB_PORT`
  - `DESKTOP_WEB_AUTO_PORT_FALLBACK`
- Appium：
  - `APPIUM_SERVER_URL`
- 远程 WS：
  - `REMOTE_WS_ENABLED`
  - `REMOTE_WS_URL`
  - `REMOTE_WS_CLIENT_ID`
  - `REMOTE_WS_HEARTBEAT_SEC`
  - `REMOTE_WS_RECONNECT_SEC`
- 报告媒体上传：
  - `REMOTE_REPORT_UPLOAD_URL`
  - `REMOTE_REPORT_UPLOAD_TOKEN`
  - `REMOTE_REPORT_UPLOAD_TIMEOUT_SEC`

## 9. 一句话总览

`desktop_web_app.py` 本质是一个“测试任务编排器 + 结果服务层”：前端通过 Flask API 触发任务，后端用子进程跑 pytest，用线程监控与收尾，再把结果落地到文件和 SQLite，并提供查询与远程控制能力。
