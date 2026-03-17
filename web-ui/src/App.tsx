import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  List,
  message,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Typography,
  Tag,
} from "antd";
import type { CSSProperties, ReactNode } from "react";

type Device = {
  serial: string;
  status: string;
  brand: string;
  model: string;
  os_version: string;
  app_versions?: Record<string, string>;
};

type AppOption = {
  key: string;
  label: string;
};

type ApiOk = {
  ok: boolean;
  error?: string;
};

type DeviceRuntimeStatus = {
  device_serial: string;
  status: string;
  task_id?: string | null;
  message?: string;
  updated_at?: string | null;
};

type TaskHistoryItem = {
  task_id: string;
  device_serial: string;
  app_key?: string;
  suite?: string;
  status: string;
  start_time?: string;
  end_time?: string | null;
  pytest_exit_code?: number | null;
  allure_exit_code?: number | null;
  error?: string | null;
  log_path?: string | null;
  allure_output?: string | null;
  has_report?: boolean;
  report_url?: string | null;
  has_report_data?: boolean;
};

type TaskReportSummary = {
  task_id: string;
  session_start?: string;
  session_end?: string;
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  total_duration: number;
  pass_rate: number;
  updated_at?: string;
};

type TaskReportCase = {
  id: number;
  task_id: string;
  case_index: number;
  node_id?: string;
  name?: string;
  status?: string;
  duration?: number;
  app?: string;
  screenshot?: string;
  video?: string;
  error_message?: string;
  screenshot_url?: string | null;
  video_url?: string | null;
};

const svgModules = import.meta.glob("../assets/*.svg", {
  eager: true,
  import: "default",
}) as Record<string, string>;

const phoneSvgMap = Object.fromEntries(
  Object.entries(svgModules).map(([path, url]) => {
    const name = path.split("/").pop()?.replace(".svg", "").toLowerCase() || "";
    return [name, url];
  })
);

function normalizeKey(value?: string): string {
  return (value || "").toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function getBrandImageUrl(brand?: string): string | null {
  const key = normalizeKey(brand);
  if (!key) return null;
  if (phoneSvgMap[key]) return phoneSvgMap[key];
  return null;
}

function renderBrand(brand?: string, imageHeight = 36): ReactNode {
  const imageUrl = getBrandImageUrl(brand);
  if (imageUrl) {
    return (
      <img
        src={imageUrl}
        alt={brand || "phone-brand"}
        title={brand || ""}
        style={{ height: imageHeight, objectFit: "contain", display: "block" }}
      />
    );
  }
  return brand || "-";
}

function formatDeviceStatus(status?: string): string {
  const s = (status || "").toLowerCase();
  if (s === "device") return "已连接";
  if (s === "offline") return "离线";
  if (s === "unauthorized") return "未授权";
  if (s === "recovery") return "恢复模式";
  return status || "-";
}

function formatRunStatus(status?: string): string {
  const s = (status || "").toLowerCase();
  if (s === "running") return "运行中";
  if (s === "failed") return "失败";
  if (s === "success") return "成功";
  if (s === "idle") return "空闲";
  if (s === "stopped") return "已停止";
  return status || "空闲";
}

function formatExitCode(code?: number | null): string {
  if (code === null || code === undefined) return "-";
  if (code === 0) return "成功";
  if (code === 1) return "失败";
  return `失败(退出码${code})`;
}

function formatCaseStatus(status?: string): string {
  const s = (status || "").toLowerCase();
  if (s === "passed") return "通过";
  if (s === "failed") return "失败";
  if (s === "skipped") return "跳过";
  return status || "-";
}

function hasReportWarning(task: TaskHistoryItem): boolean {
  const status = (task.status || "").toLowerCase();
  if (status !== "success") return false;
  if ((task.allure_exit_code ?? 0) !== 0) return true;
  const output = (task.allure_output || "").toLowerCase();
  return output.includes("failed") || output.includes("warning") || output.includes("warn");
}

async function apiRequest<T>(path: string, body?: unknown): Promise<T> {
  const resp = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }
  return (await resp.json()) as T;
}

function App() {
  const [msgApi, contextHolder] = message.useMessage();
  const [activeTab, setActiveTab] = useState("devices");
  const [devices, setDevices] = useState<Device[]>([]);
  const [apps, setApps] = useState<AppOption[]>([]);
  const [packages, setPackages] = useState<string[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>();
  const [selectedApp, setSelectedApp] = useState<string>();
  const [selectedPackage, setSelectedPackage] = useState<string>();
  const [suite, setSuite] = useState("all");
  const [executionPackages, setExecutionPackages] = useState<string[]>([]);
  const [selectedExecutionIndex, setSelectedExecutionIndex] = useState<number>(-1);
  const [logText, setLogText] = useState("等待执行...");
  const [startupMissing, setStartupMissing] = useState<string[]>([]);
  const [deviceRuntimeMap, setDeviceRuntimeMap] = useState<Record<string, DeviceRuntimeStatus>>({});
  const [currentTaskId, setCurrentTaskId] = useState<string>();
  const [taskHistory, setTaskHistory] = useState<TaskHistoryItem[]>([]);
  const [historyStatusFilter, setHistoryStatusFilter] = useState<string>("all");
  const [reportTaskId, setReportTaskId] = useState<string>();
  const [reportSummary, setReportSummary] = useState<TaskReportSummary>();
  const [reportCases, setReportCases] = useState<TaskReportCase[]>([]);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportCaseStatusFilter, setReportCaseStatusFilter] = useState<string>("all");
  const summaryCardStyle: CSSProperties = { height: 132 };
  const summaryBodyStyle: CSSProperties = {
    minHeight: 86,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };
  const summaryValueStyle: CSSProperties = { fontSize: 26, fontWeight: 700, lineHeight: 1.1 };

  const currentDevice = useMemo(
    () => devices.find((d) => d.serial === selectedDevice),
    [devices, selectedDevice]
  );
  const selectedDeviceRuntime = selectedDevice ? deviceRuntimeMap[selectedDevice] : undefined;
  const isSelectedDeviceRunning = selectedDeviceRuntime?.status === "running";
  const reportTasks = useMemo(
    () => taskHistory.filter((t) => t.has_report_data).map((t) => ({ value: t.task_id, label: `${t.task_id} | ${t.start_time || "-"}` })),
    [taskHistory]
  );
  const selectedReportTask = useMemo(
    () => taskHistory.find((t) => t.task_id === reportTaskId),
    [taskHistory, reportTaskId]
  );
  const displayTaskHistory = useMemo(() => {
    if (historyStatusFilter !== "report_warning") return taskHistory;
    return taskHistory.filter((t) => hasReportWarning(t));
  }, [taskHistory, historyStatusFilter]);
  const filteredReportCases = useMemo(() => {
    if (reportCaseStatusFilter === "all") return reportCases;
    return reportCases.filter((c) => (c.status || "").toLowerCase() === reportCaseStatusFilter);
  }, [reportCases, reportCaseStatusFilter]);

  const refreshDeviceRuntime = async (deviceSerial: string) => {
    const res = await apiRequest<{ ok: boolean; device_status: DeviceRuntimeStatus }>(
      `/api/device_status/${encodeURIComponent(deviceSerial)}`
    );
    if (res.ok && res.device_status) {
      setDeviceRuntimeMap((old) => ({ ...old, [deviceSerial]: res.device_status }));
      return res.device_status;
    }
    return null;
  };

  const refreshTaskHistory = async () => {
    const params = new URLSearchParams();
    params.set("limit", "30");
    if (selectedDevice) params.set("device", selectedDevice);
    if (historyStatusFilter !== "all" && historyStatusFilter !== "report_warning") {
      params.set("status", historyStatusFilter);
    }
    const url = `/api/task_history?${params.toString()}`;
    const res = await apiRequest<{ ok: boolean; tasks: TaskHistoryItem[] }>(url);
    if (res.ok) {
      const list = res.tasks || [];
      setTaskHistory(list);
      setReportTaskId((old) => {
        if (old && list.some((t) => t.task_id === old && t.has_report_data)) return old;
        return list.find((t) => t.has_report_data)?.task_id;
      });
    }
  };

  const refreshTaskReportData = async (taskId?: string) => {
    const targetTaskId = taskId || reportTaskId;
    if (!targetTaskId) {
      setReportSummary(undefined);
      setReportCases([]);
      return;
    }
    setReportLoading(true);
    try {
      const res = await apiRequest<
        ApiOk & { task_id: string; summary: TaskReportSummary; tests: TaskReportCase[] }
      >(`/api/task_report_data/${encodeURIComponent(targetTaskId)}`);
      if (!res.ok) {
        setReportSummary(undefined);
        setReportCases([]);
        return;
      }
      setReportSummary(res.summary);
      setReportCases(res.tests || []);
    } catch (err) {
      setReportSummary(undefined);
      setReportCases([]);
      msgApi.error(`加载任务报告失败: ${String(err)}`);
    } finally {
      setReportLoading(false);
    }
  };

  const refreshDevices = async () => {
    setLogText("正在刷新设备...");
    const res = await apiRequest<{ ok: boolean; devices: Device[]; error?: string }>(
      "/api/list_devices",
      {}
    );
    if (!res.ok) {
      setLogText(`刷新设备失败:\n${res.error || "unknown error"}`);
      return;
    }
    const list = res.devices || [];
    setDevices(list);
    for (const d of list) {
      await refreshDeviceRuntime(d.serial);
    }
    if (list.length > 0) {
      setSelectedDevice((old) => old && list.some((d) => d.serial === old) ? old : list[0].serial);
    } else {
      setSelectedDevice(undefined);
      setLogText("未找到可用设备，请检查 adb devices。");
    }
  };

  const refreshApps = async () => {
    const res = await apiRequest<AppOption[]>("/api/get_app_options");
    setApps(res || []);
    if (res?.length) {
      setSelectedApp((old) => old && res.some((a) => a.key === old) ? old : res[0].key);
    }
  };

  const refreshPackages = async (appKey?: string) => {
    const targetApp = appKey || selectedApp;
    if (!targetApp) return;
    const res = await apiRequest<{ ok: boolean; packages: string[]; error?: string }>(
      "/api/list_test_packages",
      { app_key: targetApp }
    );
    if (!res.ok) {
      setLogText(`加载用例包失败:\n${res.error || "unknown error"}`);
      return;
    }
    const list = res.packages || [];
    setPackages(list);
    setSelectedPackage((old) => old && list.includes(old) ? old : list[0]);
    setExecutionPackages((old) => {
      const filtered = old.filter((p) => list.includes(p));
      return filtered.length ? filtered : (list[0] ? [list[0]] : []);
    });
    setSelectedExecutionIndex((old) => (old >= 0 ? old : (list.length ? 0 : -1)));
    setLogText("用例包已刷新。");
  };

  const addSelectedCase = () => {
    if (!selectedPackage) return;
    if (executionPackages.includes(selectedPackage)) {
      msgApi.info("该用例已在待执行列表中");
      setSelectedExecutionIndex(executionPackages.indexOf(selectedPackage));
      return;
    }
    const next = [...executionPackages, selectedPackage];
    setExecutionPackages(next);
    setSelectedExecutionIndex(next.length - 1);
  };

  const addAllCases = () => {
    let added = 0;
    let skipped = 0;
    const next = [...executionPackages];
    for (const p of packages) {
      if (next.includes(p)) {
        skipped += 1;
      } else {
        next.push(p);
        added += 1;
      }
    }
    setExecutionPackages(next);
    if (next.length) setSelectedExecutionIndex(next.length - 1);
    msgApi.info(`批量添加完成：新增 ${added}，跳过重复 ${skipped}`);
  };

  const removeSelectedCase = () => {
    if (selectedExecutionIndex < 0 || selectedExecutionIndex >= executionPackages.length) return;
    const next = executionPackages.filter((_, idx) => idx !== selectedExecutionIndex);
    setExecutionPackages(next);
    setSelectedExecutionIndex(Math.min(selectedExecutionIndex, next.length - 1));
  };

  const moveSelectedCase = (offset: number) => {
    const from = selectedExecutionIndex;
    const to = from + offset;
    if (from < 0 || from >= executionPackages.length) return;
    if (to < 0 || to >= executionPackages.length) return;
    const next = [...executionPackages];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    setExecutionPackages(next);
    setSelectedExecutionIndex(to);
  };

  const runTests = async () => {
    try {
      const appium = await apiRequest<{ running: boolean; server_url?: string; error?: string }>(
        "/api/appium_ready"
      );
      if (!appium.running) {
        const addr = appium.server_url || "http://127.0.0.1:4723";
        msgApi.error(`Appium 未启动（${addr}）`);
        setLogText(`执行已取消：Appium 未启动\n地址: ${addr}\n详情: ${appium.error || "unknown error"}`);
        setActiveTab("results");
        return;
      }
      if (!executionPackages.length) {
        msgApi.error("请先添加至少一个待执行用例");
        return;
      }
      if (!selectedDevice) {
        msgApi.error("请先选择手机设备");
        return;
      }
      if (!selectedApp) {
        msgApi.error("请先选择应用");
        return;
      }
      if (isSelectedDeviceRunning) {
        msgApi.warning("该手机已有任务在运行中，不能重复启动");
        return;
      }

      setActiveTab("results");
      setLogText(
        `正在执行测试，请稍候...\n执行顺序:\n${executionPackages
          .map((p, i) => `${i + 1}. ${p}`)
          .join("\n")}`
      );
      const res = await apiRequest<ApiOk & { task_id?: string; status?: string }>(
        "/api/run_tests",
        {
          device: selectedDevice,
          app_key: selectedApp,
          test_packages: executionPackages,
          suite,
        }
      );
      if (!res.ok) {
        setLogText(`执行失败\n\n${res.error || "unknown error"}`);
        return;
      }
      if (res.task_id) {
        setCurrentTaskId(res.task_id);
        await refreshDeviceRuntime(selectedDevice);
        await refreshTaskHistory();
        msgApi.success(`任务已启动: ${res.task_id}`);
        setLogText((old) => `${old}\n\n任务已创建: ${res.task_id}`);
      }
    } catch (err) {
      msgApi.error("启动任务失败");
      setLogText(`执行失败\n\n${String(err)}`);
    }
  };

  const stopCurrentTask = async () => {
    if (!selectedDevice) return;
    const res = await apiRequest<ApiOk & { task_id?: string; status?: string }>(
      "/api/stop_task",
      {
        task_id: currentTaskId,
        device: selectedDevice,
      }
    );
    if (!res.ok) {
      msgApi.error(res.error || "停止任务失败");
      return;
    }
    msgApi.info("停止请求已发送");
    await refreshDeviceRuntime(selectedDevice);
    await refreshTaskHistory();
  };

  const openReport = async () => {
    const res = await apiRequest<ApiOk>("/api/open_report", {});
    if (!res.ok) {
      msgApi.error(res.error || "打开报告失败");
    }
  };

  const refreshSelectedDeviceStatus = async () => {
    if (!selectedDevice) {
      msgApi.warning("请先选择手机设备");
      return;
    }
    const s = await refreshDeviceRuntime(selectedDevice);
    if (s?.status === "running" && s.task_id) {
      setCurrentTaskId((old) => old || s.task_id || undefined);
    } else if (s && s.status !== "running") {
      setCurrentTaskId(undefined);
    }
  };

  const refreshCurrentTaskStatus = async () => {
    if (!currentTaskId) {
      msgApi.warning("当前没有可刷新的任务");
      return;
    }
    try {
      const res = await apiRequest<
        ApiOk & {
          task_id?: string;
          status?: string;
          pytest_exit_code?: number | null;
          allure_exit_code?: number | null;
          pytest_output?: string;
          allure_output?: string;
          error?: string;
          device?: string;
        }
      >(`/api/task_status/${encodeURIComponent(currentTaskId)}`);
      if (!res.ok) return;
      setLogText(
        `任务: ${res.task_id}\n状态: ${formatRunStatus(res.status)}\nPytest结果: ${formatExitCode(
          res.pytest_exit_code
        )}\n报告结果: ${formatExitCode(res.allure_exit_code)}\n\n${res.pytest_output || ""}\n\n--- 报告输出 ---\n${
          res.allure_output || ""
        }${res.error ? `\n\n错误: ${res.error}` : ""}`
      );
      if (res.status && ["success", "failed", "stopped"].includes(res.status)) {
        setCurrentTaskId(undefined);
        if (selectedDevice) await refreshDeviceRuntime(selectedDevice);
        await refreshTaskHistory();
        msgApi.info(`任务已结束: ${res.status}`);
      }
    } catch {
      msgApi.error("刷新任务状态失败");
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const startup = await apiRequest<{ missing_dependencies?: string[] }>("/api/startup_info");
        setStartupMissing(startup.missing_dependencies || []);
        await refreshApps();
        await refreshDevices();
        await refreshTaskHistory();
      } catch (err) {
        setLogText(`页面初始化失败:\n${String(err)}`);
      }
    })();
  }, []);

  useEffect(() => {
    if (selectedApp) {
      refreshPackages(selectedApp);
    }
  }, [selectedApp]);

  useEffect(() => {
    refreshTaskHistory();
  }, [selectedDevice, historyStatusFilter]);

  useEffect(() => {
    if (!selectedDevice) return;
    refreshDeviceRuntime(selectedDevice).then((s) => {
      if (s?.status === "running" && s.task_id) {
        setCurrentTaskId(s.task_id);
      }
    });
  }, [selectedDevice]);

  useEffect(() => {
    if (!currentTaskId) return;
    refreshCurrentTaskStatus();
  }, [currentTaskId, selectedDevice]);

  useEffect(() => {
    if (!reportTaskId) return;
    refreshTaskReportData(reportTaskId);
  }, [reportTaskId]);

  return (
    <div style={{ width: "calc(100% - 24px)", maxWidth: "none", margin: "8px 12px 16px", padding: 0 }}>
      {contextHolder}
      <Typography.Title level={3} style={{ marginTop: 4 }}>
        移动自动化测试桌面端
      </Typography.Title>

      {startupMissing.length > 0 && (
        <Alert
          style={{ marginBottom: 12 }}
          type="warning"
          showIcon
          message={`系统缺少依赖: ${startupMissing.join(", ")}，请先安装并加入 PATH。`}
        />
      )}

      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            { key: "devices", label: "手机终端" },
            { key: "runner", label: "用例执行" },
            { key: "results", label: "执行结果" },
            { key: "report", label: "测试报告" },
          ]}
        />
      </Card>

      {activeTab === "devices" && (
        <Card title="当前连接的手机终端">
          <Space style={{ marginBottom: 12 }}>
            <Button onClick={refreshDevices}>刷新设备</Button>
          </Space>
          <Table<Device>
            rowKey="serial"
            pagination={false}
            dataSource={devices}
            columns={[
              { title: "设备序列号", dataIndex: "serial" },
              { title: "状态", render: (_, d) => formatDeviceStatus(d.status) },
              { title: "任务状态", render: (_, d) => formatRunStatus(deviceRuntimeMap[d.serial]?.status) },
              {
                title: "品牌",
                render: (_, d) => renderBrand(d.brand, 32),
              },
              {
                title: "型号",
                dataIndex: "model",
              },
              { title: "系统", dataIndex: "os_version" },
              {
                title: "应用版本",
                render: (_, d) =>
                  `Lysora: ${(d.app_versions && d.app_versions.lysora) || "-"} / Ruijie: ${
                    (d.app_versions && d.app_versions.ruijieCloud) || "-"
                  }`,
              },
            ]}
          />
        </Card>
      )}

      {activeTab === "runner" && (
        <Card title="选择终端、测试用例并执行">
          <Row gutter={[12, 12]}>
            <Col span={6}>
              <label>手机设备</label>
              <Select
                style={{ width: "100%" }}
                value={selectedDevice}
                onChange={setSelectedDevice}
                options={devices.map((d) => ({ value: d.serial, label: `${d.serial} (${formatDeviceStatus(d.status)})` }))}
              />
            </Col>
            <Col span={6}>
              <label>应用</label>
              <Select
                style={{ width: "100%" }}
                value={selectedApp}
                onChange={setSelectedApp}
                options={apps.map((a) => ({ value: a.key, label: a.label }))}
              />
            </Col>
            <Col span={6}>
              <label>可选用例</label>
              <Select
                style={{ width: "100%" }}
                value={selectedPackage}
                onChange={setSelectedPackage}
                options={packages.map((p) => ({ value: p, label: p }))}
              />
            </Col>
            <Col span={6}>
              <label>测试范围</label>
              <Select
                style={{ width: "100%" }}
                value={suite}
                onChange={setSuite}
                options={[
                  { value: "all", label: "全部" },
                  { value: "smoke", label: "smoke" },
                  { value: "full", label: "full" },
                ]}
              />
            </Col>
          </Row>

          <Space style={{ marginTop: 12 }}>
            <Button htmlType="button" onClick={refreshSelectedDeviceStatus}>刷新设备状态</Button>
            <Button htmlType="button" onClick={() => refreshPackages()}>刷新用例包</Button>
            <Button
              htmlType="button"
              type="primary"
              onClick={(ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                void runTests();
              }}
              disabled={isSelectedDeviceRunning}
            >
              启动执行
            </Button>
            <Button htmlType="button" danger onClick={stopCurrentTask} disabled={!isSelectedDeviceRunning}>
              停止任务
            </Button>
          </Space>

          <Card
            size="small"
            style={{ marginTop: 12, background: "#fafafa" }}
            title="待执行用例（按列表顺序执行）"
            extra={
              <Space wrap>
                <Button size="small" onClick={addSelectedCase}>
                  添加
                </Button>
                <Button size="small" onClick={addAllCases}>
                  添加全部
                </Button>
                <Button size="small" onClick={removeSelectedCase}>
                  移除
                </Button>
                <Button size="small" onClick={() => moveSelectedCase(-1)}>
                  上移
                </Button>
                <Button size="small" onClick={() => moveSelectedCase(1)}>
                  下移
                </Button>
                <Button
                  size="small"
                  onClick={() => {
                    setExecutionPackages([]);
                    setSelectedExecutionIndex(-1);
                  }}
                >
                  清空
                </Button>
              </Space>
            }
          >
            <List
              bordered
              dataSource={executionPackages}
              renderItem={(item, idx) => (
                <List.Item
                  onClick={() => setSelectedExecutionIndex(idx)}
                  style={{
                    cursor: "pointer",
                    background: selectedExecutionIndex === idx ? "#e8f0fe" : undefined,
                  }}
                >
                  {idx + 1}. {item}
                </List.Item>
              )}
            />
          </Card>

          <Row gutter={10} style={{ marginTop: 12 }}>
            <Col span={5}>
              <Card size="small" title="手机品牌" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                {renderBrand(currentDevice?.brand, 56)}
              </Card>
            </Col>
            <Col span={5}>
              <Card size="small" title="设备型号" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                <span style={summaryValueStyle}>{currentDevice?.model || "-"}</span>
              </Card>
            </Col>
            <Col span={5}>
              <Card size="small" title="系统版本" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                <span style={summaryValueStyle}>{currentDevice?.os_version || "-"}</span>
              </Card>
            </Col>
            <Col span={4}>
              <Card size="small" title="Lysora 版本" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                <span style={summaryValueStyle}>
                  {(currentDevice?.app_versions && currentDevice.app_versions.lysora) || "-"}
                </span>
              </Card>
            </Col>
            <Col span={5}>
              <Card size="small" title="ruijieCloud 版本" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                <span style={summaryValueStyle}>
                  {(currentDevice?.app_versions && currentDevice.app_versions.ruijieCloud) || "-"}
                </span>
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {activeTab === "results" && (
        <Card
          title="测试用例结果"
          extra={
            <Space>
              <Select
                style={{ width: 150 }}
                value={historyStatusFilter}
                onChange={setHistoryStatusFilter}
                options={[
                  { value: "all", label: "全部状态" },
                  { value: "running", label: "运行中" },
                  { value: "success", label: "成功" },
                  { value: "failed", label: "失败" },
                  { value: "stopped", label: "已停止" },
                  { value: "report_warning", label: "仅报告告警" },
                ]}
              />
              <Button onClick={refreshTaskHistory}>刷新历史</Button>
              <Button onClick={refreshCurrentTaskStatus} disabled={!currentTaskId}>
                刷新任务状态
              </Button>
              <Button onClick={openReport}>打开最近报告</Button>
            </Space>
          }
        >
          <Table<TaskHistoryItem>
            rowKey="task_id"
            size="small"
            pagination={{ pageSize: 8, hideOnSinglePage: true }}
            dataSource={displayTaskHistory}
            onRow={(record) => ({
              onClick: () => {
                setCurrentTaskId(record.task_id);
                if (record.has_report_data) {
                  setReportTaskId(record.task_id);
                }
                setActiveTab("results");
              },
              style: { cursor: "pointer" },
            })}
            columns={[
              { title: "任务ID", dataIndex: "task_id", width: 130 },
              { title: "设备", dataIndex: "device_serial", width: 140 },
              {
                title: "状态",
                render: (_, r) => {
                  const s = (r.status || "").toLowerCase();
                  const color =
                    s === "success" ? "green" :
                    s === "failed" ? "red" :
                    s === "running" ? "blue" :
                    s === "stopped" ? "orange" : "default";
                  const warn = hasReportWarning(r);
                  return (
                    <Space size={6}>
                      <Tag color={color}>{formatRunStatus(r.status)}</Tag>
                      {warn && <Tag color="gold" title={r.allure_output || "报告后处理存在告警"}>报告告警</Tag>}
                    </Space>
                  );
                },
                width: 190,
              },
              { title: "开始时间", dataIndex: "start_time", width: 170 },
              { title: "结束时间", dataIndex: "end_time", width: 170 },
              { title: "Pytest结果", render: (_, r) => formatExitCode(r.pytest_exit_code), width: 120 },
              { title: "报告结果", render: (_, r) => formatExitCode(r.allure_exit_code), width: 120 },
              {
                title: "操作",
                width: 180,
                render: (_, r) => (
                  <Space size={6}>
                    <Button
                      size="small"
                      disabled={!r.has_report}
                      onClick={(ev) => {
                        ev.stopPropagation();
                        if (!r.has_report) return;
                        const url = r.report_url || `/api/task_report/${encodeURIComponent(r.task_id)}`;
                        window.open(url, "_blank");
                      }}
                    >
                      查看报告
                    </Button>
                    <Button
                      size="small"
                      onClick={(ev) => {
                        ev.stopPropagation();
                        window.open(`/api/task_log/${encodeURIComponent(r.task_id)}`, "_blank");
                      }}
                    >
                      下载日志
                    </Button>
                  </Space>
                ),
              },
            ]}
            style={{ marginBottom: 12 }}
          />
          <pre
            style={{
              margin: 0,
              whiteSpace: "pre-wrap",
              background: "#0f172a",
              color: "#e2e8f0",
              borderRadius: 8,
              padding: 10,
              minHeight: 180,
              maxHeight: 460,
              overflow: "auto",
              fontSize: 12,
            }}
          >
            {logText}
          </pre>
        </Card>
      )}

      {activeTab === "report" && (
        <Card
          title="测试报告"
          extra={
            <Space wrap>
              <Select
                style={{ width: 340 }}
                placeholder="选择任务"
                value={reportTaskId}
                onChange={(v) => setReportTaskId(v)}
                options={reportTasks}
              />
              <Select
                style={{ width: 120 }}
                value={reportCaseStatusFilter}
                onChange={setReportCaseStatusFilter}
                options={[
                  { value: "all", label: "全部状态" },
                  { value: "passed", label: "通过" },
                  { value: "failed", label: "失败" },
                  { value: "skipped", label: "跳过" },
                ]}
              />
              <Button onClick={() => refreshTaskReportData()}>刷新报告</Button>
              <Button
                disabled={!selectedReportTask?.has_report}
                onClick={() => {
                  if (!selectedReportTask?.has_report) return;
                  const url = selectedReportTask.report_url || `/api/task_report/${encodeURIComponent(selectedReportTask.task_id)}`;
                  window.open(url, "_blank");
                }}
              >
                打开HTML报告
              </Button>
            </Space>
          }
        >
          {!reportTaskId && (
            <Alert
              type="info"
              showIcon
              message="暂无可用任务报告，请先执行至少一次测试任务。"
              style={{ marginBottom: 12 }}
            />
          )}
          {reportSummary && (
            <Row gutter={10} style={{ marginBottom: 12 }}>
              <Col span={4}>
                <Card size="small" title="总计">
                  <Typography.Title level={4} style={{ margin: 0 }}>{reportSummary.total}</Typography.Title>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small" title="通过">
                  <Typography.Title level={4} style={{ margin: 0, color: "#16a34a" }}>{reportSummary.passed}</Typography.Title>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small" title="失败">
                  <Typography.Title level={4} style={{ margin: 0, color: "#dc2626" }}>{reportSummary.failed}</Typography.Title>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small" title="跳过">
                  <Typography.Title level={4} style={{ margin: 0, color: "#d97706" }}>{reportSummary.skipped}</Typography.Title>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small" title="通过率">
                  <Typography.Title level={4} style={{ margin: 0 }}>{(reportSummary.pass_rate || 0).toFixed(1)}%</Typography.Title>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small" title="总耗时">
                  <Typography.Title level={4} style={{ margin: 0 }}>{(reportSummary.total_duration || 0).toFixed(1)}s</Typography.Title>
                </Card>
              </Col>
            </Row>
          )}
          <Table<TaskReportCase>
            rowKey={(r) => `${r.task_id}-${r.case_index}`}
            size="small"
            loading={reportLoading}
            pagination={{ pageSize: 10, hideOnSinglePage: true }}
            dataSource={filteredReportCases}
            expandable={{
              expandedRowRender: (record) => (
                <div>
                  <div><b>节点:</b> {record.node_id || "-"}</div>
                  <div style={{ marginTop: 6 }}>
                    <b>错误:</b> {record.error_message || "-"}
                  </div>
                  <Space style={{ marginTop: 8 }}>
                    <Button
                      size="small"
                      disabled={!record.screenshot_url}
                      onClick={() => record.screenshot_url && window.open(record.screenshot_url, "_blank")}
                    >
                      查看截图
                    </Button>
                    <Button
                      size="small"
                      disabled={!record.video_url}
                      onClick={() => record.video_url && window.open(record.video_url, "_blank")}
                    >
                      查看视频
                    </Button>
                  </Space>
                  {record.screenshot_url && (
                    <div style={{ marginTop: 8 }}>
                      <img
                        src={record.screenshot_url}
                        alt={record.name || "screenshot"}
                        style={{ maxHeight: 240, maxWidth: "100%", border: "1px solid #ddd", borderRadius: 6 }}
                      />
                    </div>
                  )}
                </div>
              ),
            }}
            columns={[
              { title: "#", dataIndex: "case_index", width: 50 },
              { title: "测试用例", dataIndex: "name", ellipsis: true },
              {
                title: "状态",
                width: 90,
                render: (_, r) => {
                  const s = (r.status || "").toLowerCase();
                  const color = s === "passed" ? "green" : s === "failed" ? "red" : s === "skipped" ? "orange" : "default";
                  return <Tag color={color}>{formatCaseStatus(r.status)}</Tag>;
                },
              },
              {
                title: "耗时",
                width: 90,
                render: (_, r) => `${(r.duration || 0).toFixed(2)}s`,
              },
              { title: "应用", dataIndex: "app", width: 100 },
            ]}
          />
        </Card>
      )}
    </div>
  );
}

export default App;
