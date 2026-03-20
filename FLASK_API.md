# Flask 接口文档

本文档基于当前模块化实现整理（`desktop_web_app.py` 入口 + `desktop_app/api.py` 路由），覆盖所有 Flask 路由。

## 基本信息

- 基础地址：`http://127.0.0.1:17999`
- 数据格式：JSON（文件下载接口除外）
- 鉴权：当前无鉴权

---

## 页面与静态资源

### 1) 首页
- 方法：`GET`
- 路径：`/`
- 说明：返回前端入口页面 `ui/index.html`
- 响应：HTML 文件

### 2) 前端静态资源
- 方法：`GET`
- 路径：`/assets/<path:filename>`
- 说明：返回前端打包后的静态资源（js/css/svg 等）
- 响应：静态文件

---

## 设备与基础信息

### 3) 获取设备列表
- 方法：`POST`
- 路径：`/api/list_devices`
- 请求体：无（可传空对象）
- 成功响应示例：

```json
{
  "ok": true,
  "devices": [
    {
      "serial": "R5CW50Y8TMT",
      "status": "device",
      "brand": "samsung",
      "model": "SM-S9160",
      "os_version": "13",
      "app_versions": {
        "lysora": "1.0.1",
        "ruijieCloud": "9.6.1"
      }
    }
  ]
}
```

- 失败响应示例：

```json
{
  "ok": false,
  "devices": [],
  "error": "无法执行 adb devices"
}
```

### 4) 获取应用选项
- 方法：`GET`
- 路径：`/api/get_app_options`
- 响应示例：

```json
[
  { "key": "lysora", "label": "Lysora" },
  { "key": "ruijieCloud", "label": "RuijieCloud" }
]
```

### 5) 获取可执行测试包
- 方法：`POST`
- 路径：`/api/list_test_packages`
- 请求体：

```json
{
  "app_key": "lysora"
}
```

- 响应示例：

```json
{
  "ok": true,
  "packages": [
    {
      "value": "tests/lysora",
      "label": "该应用全部用例",
      "tooltip": "执行该应用目录下全部测试文件"
    },
    {
      "value": "tests/lysora/test_lysora_home_logo.py",
      "label": "Lysora 首页 Logo 显示检查",
      "tooltip": "Lysora 首页 Logo 显示检查"
    }
  ],
  "package_paths": [
    "tests/lysora",
    "tests/lysora/test_lysora_home_logo.py"
  ]
}
```

- 说明：
  - `packages` 为对象数组（`value/label/tooltip`），前端用于中文展示与提示。
  - `package_paths` 为兼容旧前端保留的纯路径数组。

### 6) 启动信息检查
- 方法：`GET`
- 路径：`/api/startup_info`
- 响应示例：

```json
{
  "ok": true,
  "missing_dependencies": []
}
```

### 7) Appium 就绪检查
- 方法：`GET`
- 路径：`/api/appium_ready`
- 响应示例：

```json
{
  "ok": true,
  "running": true,
  "server_url": "http://127.0.0.1:4723",
  "error": null
}
```

---

## 任务执行与状态

### 8) 启动测试任务
- 方法：`POST`
- 路径：`/api/run_tests`
- 请求体：

```json
{
  "device": "R5CW50Y8TMT",
  "app_key": "lysora",
  "test_packages": ["tests/lysora/test_lysora_home_logo.py"],
  "suite": "all"
}
```

> 兼容字段：`test_package`（单个字符串），当 `test_packages` 为空时使用。

- 成功响应：

```json
{
  "ok": true,
  "task_id": "fc89de8a4782",
  "status": "running"
}
```

- 失败响应示例：

```json
{
  "ok": false,
  "error": "Appium 未启动，请先启动后再执行测试。地址: http://127.0.0.1:4723，详情: <detail>"
}
```

### 9) 获取任务状态
- 方法：`GET`
- 路径：`/api/task_status/<task_id>`
- 响应字段（核心）：
  - `ok`
  - `task_id`
  - `device`
  - `status`：`running/success/failed/stopped`
  - `pytest_exit_code`
  - `allure_exit_code`
  - `allure_output`
  - `error`
  - `has_report`
  - `report_url`
  - `has_report_data`
  - `pytest_output`（任务日志文本末尾）

### 10) 停止任务
- 方法：`POST`
- 路径：`/api/stop_task`
- 请求体（至少传一个）：

```json
{
  "task_id": "fc89de8a4782",
  "device": "R5CW50Y8TMT"
}
```

- 响应示例：

```json
{
  "ok": true,
  "task_id": "fc89de8a4782",
  "status": "stopped"
}
```

### 11) 查询设备运行态
- 方法：`GET`
- 路径：`/api/device_status/<device_serial>`
- 响应示例：

```json
{
  "ok": true,
  "device_status": {
    "device_serial": "R5CW50Y8TMT",
    "status": "idle",
    "task_id": null,
    "message": "",
    "updated_at": "2026-03-17 17:52:33"
  }
}
```

---

## 历史任务与日志

### 12) 历史任务列表
- 方法：`GET`
- 路径：`/api/task_history`
- 查询参数：
  - `limit`：默认 `20`，最大 `200`
  - `device`：按设备过滤
  - `status`：`running/success/failed/stopped`

- 响应示例：

```json
{
  "ok": true,
  "tasks": [
    {
      "task_id": "fc89de8a4782",
      "device_serial": "R5CW50Y8TMT",
      "app_key": "lysora",
      "suite": "all",
      "test_packages": "[\"tests/lysora\"]",
      "status": "success",
      "start_time": "2026-03-17 17:50:57",
      "end_time": "2026-03-17 17:51:48",
      "pytest_exit_code": 0,
      "allure_exit_code": 0,
      "error": null,
      "log_path": "reports/task-logs/fc89de8a4782.log",
      "allure_output": "HTML report generated: reports/task-reports/fc89de8a4782/test_report.html",
      "has_report": true,
      "report_url": "/api/task_report/fc89de8a4782",
      "has_report_data": true
    }
  ]
}
```

### 13) 下载任务日志
- 方法：`GET`
- 路径：`/api/task_log/<task_id>`
- 说明：返回日志文件下载（`text/plain`）
- 失败状态：
  - `404`：任务不存在或日志不存在

---

## 测试报告

### 14) 打开任务 HTML 报告
- 方法：`GET`
- 路径：`/api/task_report/<task_id>`
- 说明：返回该任务 HTML 报告文件
- 失败状态：
  - `404`：报告不存在

### 15) 获取任务报告结构化数据（SQLite）
- 方法：`GET`
- 路径：`/api/task_report_data/<task_id>`
- 响应结构：

```json
{
  "ok": true,
  "task_id": "fc89de8a4782",
  "summary": {
    "task_id": "fc89de8a4782",
    "session_start": "2026-03-17T17:50:57.234",
    "session_end": "2026-03-17T17:51:48.002",
    "total": 2,
    "passed": 2,
    "failed": 0,
    "skipped": 0,
    "total_duration": 47.61,
    "pass_rate": 100.0,
    "updated_at": "2026-03-17 17:51:49"
  },
  "tests": [
    {
      "id": 1,
      "task_id": "fc89de8a4782",
      "case_index": 1,
      "node_id": "tests/lysora/test_lysora_home_logo.py::test_lysora_home_has_logo",
      "name": "test_lysora_home_has_logo",
      "status": "passed",
      "duration": 12.34,
      "app": "lysora",
      "screenshot": "reports/screenshots/...",
      "video": "reports/videos/...",
      "error_message": "",
      "screenshot_url": "/api/report_asset?path=reports/screenshots/...",
      "video_url": "/api/report_asset?path=reports/videos/..."
    }
  ]
}
```

- 失败状态：
  - `404`：报告数据不存在

### 16) 报告资源访问（图片/视频）
- 方法：`GET`
- 路径：`/api/report_asset`
- 查询参数：
  - `path`：如 `reports/videos/lysora/xxx.mp4`
- 成功：返回实际文件流
- 失败状态：
  - `400`：`path` 为空
  - `404`：文件不存在或路径非法

### 17) 打开最近报告（本机）
- 方法：`POST`
- 路径：`/api/open_report`
- 说明：调用系统 `os.startfile` 打开 `reports/test_report.html`
- 响应：

```json
{
  "ok": true
}
```

---

## 状态码约定

- `200`：业务成功（部分失败也可能用 `ok=false` 表示）
- `400`：请求参数问题（如缺少必填）
- `403`：路径非法（文件访问安全校验）
- `404`：资源不存在（任务/日志/报告/文件）

---

## 备注

- `task_history` 中 `test_packages` 当前以 JSON 字符串存储（SQLite 文本字段），前端可按需解析。
- 打包模式（PyInstaller）下，资源路径会在运行目录与 `_internal` 之间做兼容查找。
