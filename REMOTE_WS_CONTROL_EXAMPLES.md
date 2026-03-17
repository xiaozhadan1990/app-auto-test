# 远程 WebSocket 控制联调示例

本文档用于联调：

- 服务端：`ruiyi-test-server`
- 客户端：`app-auto-test`（`desktop_web_app.py`）

---

## 1. 客户端配置

在客户端 `.env` 中启用远程 WS：

```env
REMOTE_WS_ENABLED=true
REMOTE_WS_URL=ws://<server-host>:<server-port>/api/v1/ws/client
REMOTE_WS_CLIENT_ID=desktop-lab-01
REMOTE_WS_HEARTBEAT_SEC=15
REMOTE_WS_RECONNECT_SEC=5
REMOTE_WS_PING_INTERVAL_SEC=20
REMOTE_WS_PING_TIMEOUT_SEC=10
```

然后启动客户端（桌面端 Flask）：

```powershell
python desktop_web_app.py
```

可本地查看连接状态：

```bash
curl "http://127.0.0.1:17999/api/remote_ws_status"
```

---

## 2. 服务端接口

### 2.1 查询在线客户端

```bash
curl "http://<server-host>:<server-port>/api/v1/ws/client/list"
```

返回示例：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "client_id": "desktop-lab-01",
      "address": "192.168.1.88:52340",
      "last_seen": 1760000000,
      "last_heartbeat": 1760000000,
      "online": true,
      "meta": {
        "hostname": "DESKTOP-001",
        "pid": 12345,
        "status": "online",
        "version": "desktop-web-app"
      }
    }
  ]
}
```

### 2.2 下发命令（统一入口）

- 方法：`POST /api/v1/ws/client/command`
- body：
  - `client_id`：目标客户端 ID
  - `action`：命令名
  - `payload`：命令参数
  - `timeout_ms`：超时（可选）

---

## 3. 常用命令示例

> 以下示例默认服务端地址为：`http://127.0.0.1:8080`
>  
> 若你服务端有鉴权中间件，需要按你现有方式补 token/header。

### 3.1 列出设备

```bash
curl -X POST "http://127.0.0.1:8090/api/v1/ws/client/command" ^
  -H "Content-Type: application/json" ^
  -d "{\"client_id\":\"desktop-lab-01\",\"action\":\"list_devices\",\"payload\":{}}"
```

### 3.2 列出测试包

```bash
curl -X POST "http://127.0.0.1:8090/api/v1/ws/client/command" ^
  -H "Content-Type: application/json" ^
  -d "{\"client_id\":\"desktop-lab-01\",\"action\":\"list_test_packages\",\"payload\":{\"app_key\":\"lysora\"}}"
```

### 3.3 启动测试（run_tests）

```bash
curl -X POST "http://127.0.0.1:8090/api/v1/ws/client/command" ^
  -H "Content-Type: application/json" ^
  -d "{\"client_id\":\"desktop-lab-01\",\"action\":\"run_tests\",\"timeout_ms\":20000,\"payload\":{\"device\":\"R5CW50Y8TMT\",\"app_key\":\"lysora\",\"test_packages\":[\"tests/lysora/test_lysora_home_logo.py\"],\"suite\":\"all\"}}"
```

### 3.4 查询任务状态

```bash
curl -X POST "http://127.0.0.1:8080/api/v1/ws/client/command" ^
  -H "Content-Type: application/json" ^
  -d "{\"client_id\":\"desktop-lab-01\",\"action\":\"task_status\",\"payload\":{\"task_id\":\"fc89de8a4782\"}}"
```

### 3.5 停止任务

```bash
curl -X POST "http://127.0.0.1:8080/api/v1/ws/client/command" ^
  -H "Content-Type: application/json" ^
  -d "{\"client_id\":\"desktop-lab-01\",\"action\":\"stop_task\",\"payload\":{\"task_id\":\"fc89de8a4782\"}}"
```

### 3.6 查询任务历史

```bash
curl -X POST "http://127.0.0.1:8080/api/v1/ws/client/command" ^
  -H "Content-Type: application/json" ^
  -d "{\"client_id\":\"desktop-lab-01\",\"action\":\"task_history\",\"payload\":{\"limit\":20,\"status\":\"success\"}}"
```

### 3.7 查询设备运行状态

```bash
curl -X POST "http://127.0.0.1:8080/api/v1/ws/client/command" ^
  -H "Content-Type: application/json" ^
  -d "{\"client_id\":\"desktop-lab-01\",\"action\":\"device_status\",\"payload\":{\"device_serial\":\"R5CW50Y8TMT\"}}"
```

### 3.8 查询 Appium 就绪

```bash
curl -X POST "http://127.0.0.1:8080/api/v1/ws/client/command" ^
  -H "Content-Type: application/json" ^
  -d "{\"client_id\":\"desktop-lab-01\",\"action\":\"appium_ready\",\"payload\":{}}"
```

---

## 4. 响应结构说明

服务端会返回统一结构（示意）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "type": "response",
    "client_id": "desktop-lab-01",
    "request_id": "xxxxx",
    "action": "run_tests",
    "data": {
      "ok": true,
      "task_id": "fc89de8a4782",
      "status": "running"
    },
    "ok": true
  }
}
```

---

## 5. 故障排查

- 看不到客户端：
  - 检查 `REMOTE_WS_ENABLED=true`
  - 检查 `REMOTE_WS_URL` 地址和端口
  - 检查服务端 `/api/v1/ws/client` 是否可达
- 命令超时：
  - 增大 `timeout_ms`
  - 查看客户端本地接口：`/api/remote_ws_status`
- 命令返回 `unsupported action`：
  - 核对 `action` 是否在当前支持列表中

