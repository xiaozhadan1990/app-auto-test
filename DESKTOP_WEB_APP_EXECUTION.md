# desktop_web_app.py 执行过程说明

本文档说明当前桌面端后端的实际运行链路，按“入口 -> 依赖容器 -> API 调用 -> 测试任务 -> 报告 -> 远程控制”展开。

## 1. 程序角色与职责

- `desktop_web_app.py`：入口文件，仅负责环境加载、容器创建、启动服务。
- `desktop_app/services_container.py`：依赖容器，统一装配各业务服务与状态。
- `desktop_app/api.py` + `desktop_app/app_factory.py`：Flask 路由注册与应用创建。
- `desktop_app/task_service.py`：测试任务执行、状态查询、停止任务。
- `desktop_app/report_service.py`：报告路径/资产/入库与查询。
- `desktop_app/db_service.py`：SQLite 存取与历史查询。
- `desktop_app/remote_ws_service.py`：远程 WS 连接、心跳、命令分发。

## 1.1 模块依赖关系简图（文字版）

```text
desktop_web_app.py
  -> DesktopServiceContainer (desktop_app/services_container.py)
      -> app_factory.create_app(...)
          -> api.register_routes(...)
              -> services.* (统一由容器提供能力)

services_container
  -> task_service        (run_tests / task_status / stop_task)
  -> report_service      (报告路径、入库、读取、资产解析)
  -> db_service          (SQLite 连接、设备状态、任务历史)
  -> remote_ws_service   (连接、心跳、消息处理、命令分发)
  -> device_service      (adb 设备与 app 版本查询)
  -> package_service     (测试包列表与 case_name 显示名解析)

api.py
  -> 只做参数解析与响应封装
  -> 不直接写业务逻辑，统一委托给 services_container
```

## 2. 启动阶段（main）

入口函数：`main()`（`desktop_web_app.py`）

启动顺序：
1. 模块加载时先执行 `_load_local_env_file()`，从多个候选路径读取 `.env` 并写入环境变量（不覆盖已有变量）。
2. 模块初始化阶段：
   - 创建 `DesktopServiceContainer`（`services`）。
   - `create_app(services.build_api_deps())` 生成 Flask 应用并注册全部路由。
3. 进入 `main()` 后，先判断是否为 pytest 子进程模式：
   - 若命令行为 `--run-pytest`，直接 `pytest.main(...)` 后退出。
4. 正常服务模式下执行：
   - `services.init_runtime_db()`：初始化 SQLite 表结构。
   - `services.start_remote_ws_if_needed(...)`：若配置开启远程 WS，则启动后台线程连接。
   - 读取监听地址和端口（`DESKTOP_WEB_HOST` / `DESKTOP_WEB_PORT`）。
   - 如果启用 `DESKTOP_WEB_AUTO_PORT_FALLBACK`，调用 `services.get_free_port(...)` 自动避让端口占用。
   - 启动后台线程 `_auto_open_browser(url)` 自动打开浏览器。
   - `app.run(...)` 启动 Flask 服务。

## 3. 全局状态与数据存储

### 3.1 内存状态

- `_tasks`: 运行中任务字典，按 `task_id` 存储子进程、状态、日志路径等。
- `_device_running_task`: 设备与任务映射，用于“一台设备同一时间仅允许一个任务”。
- `_tasks_lock`: 并发读写锁。
- `services.task_runtime`: 任务运行时容器（由 `task_service` 使用）。
- `services.remote_ws_runtime`: 远程 WS 运行时容器（由 `remote_ws_service` 使用）。

### 3.2 持久化状态（SQLite）

数据库文件：`reports/runtime_state.db`

关键表：
- `device_runtime_status`: 设备实时状态（idle/running/failed 等）。
- `task_run_history`: 任务历史（开始/结束时间、退出码、错误、日志路径）。
- `task_report_summary`: 报告汇总（总数、通过率、耗时等）。
- `task_report_cases`: 用例明细（状态、截图、视频、报错等）。

## 4. HTTP 路由与核心函数映射

### 4.1 页面与静态资源

- 路由定义位置：`desktop_app/api.py`
- `GET /` -> 返回 `ui/index.html`
- `GET /assets/<path>` -> 返回前端静态资源

### 4.2 设备与配置

- `POST /api/list_devices` -> `services.list_devices()`
  - 执行 `adb devices`
  - 对在线设备补充品牌/型号/系统版本
  - 查询 `APP_CONFIG` 中各 App 包名版本
- `GET /api/get_app_options` -> 读取 `APP_CONFIG`
- `POST /api/list_test_packages` -> `services.list_test_packages(app_key)`

### 4.3 测试任务

- `POST /api/run_tests` -> `services.run_tests(payload)` -> `task_service.run_tests(...)`
- `GET /api/task_status/<task_id>` -> `services.task_status(task_id)`
- `POST /api/stop_task` -> `services.stop_task(payload)`
- `GET /api/task_history` -> `services.get_task_history(...)`
- `GET /api/device_status/<device_serial>` -> `services.get_device_status(...)`

### 4.4 报告与日志

- `GET /api/task_log/<task_id>` -> 下载任务日志
- `GET /api/task_report/<task_id>` -> 返回任务 HTML 报告
- `GET /api/task_report_data/<task_id>` -> `services.get_task_report_data(...)`
- `GET /api/report_asset?path=...` -> 安全校验后返回截图/视频文件
- `POST /api/open_report` -> `services.open_report()` 打开最新报告

### 4.5 启动检查与远程状态

- `GET /api/startup_info` -> `services.startup_info()`
- `GET /api/appium_ready` -> `services.appium_ready()`
- `GET /api/remote_ws_status` -> `services.remote_ws_status()`
- `GET /api/remote_ws_log` -> `services.read_remote_ws_log_lines(...)`

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

当前架构是“轻入口 + 模块化服务层”：`desktop_web_app.py` 负责启动，`desktop_app/*` 负责 API、任务编排、报告、数据库和远程控制能力。

## 10. 典型请求链路示例（POST /api/run_tests）

以下链路按当前实现的真实调用路径展开：

1. 前端发起 `POST /api/run_tests`，请求体包含 `device/app_key/test_packages/suite`。
2. `desktop_app/api.py` 中路由函数读取 JSON 后，调用 `services.run_tests(payload)`。
3. `services_container.run_tests(...)` 将依赖打包后，委托给 `task_service.run_tests(...)`。
4. `task_service.run_tests(...)` 完成参数与 Appium 就绪校验：
   - `services.appium_ready()` 探测 `APPIUM_SERVER_URL/status`
   - 校验 `device` 与 `test_packages`
5. 任务启动阶段：
   - 生成 `task_id`
   - 设置任务级环境变量（`APPIUM_UDID`、`TEST_RESULTS_FILE`、`TEST_REPORT_FILE`）
   - `subprocess.Popen` 启动 pytest 子进程
6. 状态落地阶段：
   - 内存态：`TaskRuntime.tasks/device_running_task`
   - 持久化：`services.insert_task_history(...)` + `services.set_device_status(...)`
7. 后台监控线程 `_watch_task`：
   - 持续读取 pytest 输出写入 `reports/task-logs/<task_id>.log`
   - 执行报告后处理与入库（`services.save_task_report_to_db(...)`）
   - 回写最终状态（success/failed/stopped）
8. 查询与展示阶段：
   - 前端轮询 `GET /api/task_status/<task_id>`
   - 任务结束后可通过 `GET /api/task_report/<task_id>` 和 `GET /api/task_report_data/<task_id>` 查看报告。
