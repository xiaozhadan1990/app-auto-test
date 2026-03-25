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
  runtime_status?: DeviceRuntimeStatus;
};

type AppOption = {
  key: string;
  label: string;
};

type TestPackageOption = {
  value: string;
  label: string;
  tooltip?: string;
};

function normalizePackageValue(input: unknown): string | undefined {
  if (typeof input === "string") {
    const trimmed = input.trim();
    return trimmed || undefined;
  }
  if (input && typeof input === "object") {
    const raw = (input as { value?: unknown }).value;
    if (typeof raw === "string") {
      const trimmed = raw.trim();
      return trimmed || undefined;
    }
  }
  return undefined;
}

function normalizePackageQueue(input: unknown[]): string[] {
  const seen = new Set<string>();
  const list: string[] = [];
  for (const item of input) {
    const value = normalizePackageValue(item);
    if (!value || seen.has(value)) continue;
    seen.add(value);
    list.push(value);
  }
  return list;
}

function fallbackPackageLabel(packageValue: string): string {
  const normalized = packageValue.replace(/\\/g, "/");
  if (!normalized.endsWith(".py")) {
    return normalized;
  }
  const segments = normalized.split("/");
  const fileName = segments[segments.length - 1] || normalized;
  const appKey = (segments[segments.length - 2] || "").toLowerCase();
  const appName =
    appKey === "lysora" ? "Lysora" : appKey === "ruijiecloud" ? "RuijieCloud" : "娴嬭瘯";
  const stem = fileName.replace(/\.py$/i, "").replace(/^test_/i, "");
  const readable = stem.replace(/_/g, " ").trim() || fileName;
  return `${appName}-${readable}`;
}

function resolvePackageLabel(input: unknown, labelMap: Record<string, string>): string {
  const value = normalizePackageValue(input);
  if (!value) return "鏈煡鐢ㄤ緥";
  return labelMap[value] || fallbackPackageLabel(value);
}

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

type ReportPagination = {
  page: number;
  page_size: number;
  total: number;
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
  // 缁熶竴鍝佺墝閿悕锛屼究浜庡仛闈欐€佽祫婧愭槧灏勫尮閰嶃€?
  return (value || "").toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function getBrandImageUrl(brand?: string): string | null {
  // 鏍规嵁鍝佺墝鍚嶈繑鍥炲搴旂殑鏈湴 SVG 鍥剧墖鍦板潃銆?
  const key = normalizeKey(brand);
  if (!key) return null;
  if (phoneSvgMap[key]) return phoneSvgMap[key];
  return null;
}

function renderBrand(brand?: string, imageHeight = 36): ReactNode {
  // 浼樺厛娓叉煋鍝佺墝鍥炬爣锛屾壘涓嶅埌鍥炬爣鏃跺洖閫€涓烘枃鏈€?
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
  // 灏?ADB 璁惧鐘舵€佽浆鎹负鐣岄潰灞曠ず鏂囨銆?
  const s = (status || "").toLowerCase();
  if (s === "device") return "已连接";
  if (s === "offline") return "绂荤嚎";
  if (s === "unauthorized") return "未授权";
  if (s === "recovery") return "鎭㈠妯″紡";
  return status || "-";
}

function formatRunStatus(status?: string): string {
  // 灏嗕换鍔¤繍琛岀姸鎬佽浆鎹负鐣岄潰灞曠ず鏂囨銆?
  const s = (status || "").toLowerCase();
  if (s === "running") return "运行中";
  if (s === "failed") return "澶辫触";
  if (s === "success") return "鎴愬姛";
  if (s === "idle") return "绌洪棽";
  if (s === "stopped") return "已停止";
  return status || "绌洪棽";
}

function formatExitCode(code?: number | null): string {
  // 灏嗚繘绋嬮€€鍑虹爜鏄犲皠涓烘槗璇荤粨鏋滄枃妗堛€?
  if (code === null || code === undefined) return "-";
  if (code === 0) return "鎴愬姛";
  if (code === 1) return "澶辫触";
  return `澶辫触(閫€鍑虹爜${code})`;
}

function formatCaseStatus(status?: string): string {
  // 灏嗙敤渚嬫墽琛岀姸鎬佽浆鎹负鐣岄潰灞曠ず鏂囨銆?
  const s = (status || "").toLowerCase();
  if (s === "passed") return "閫氳繃";
  if (s === "failed") return "澶辫触";
  if (s === "skipped") return "璺宠繃";
  return status || "-";
}

function hasReportWarning(task: TaskHistoryItem): boolean {
  // 璇嗗埆浠诲姟鏄惁瀛樺湪鈥滄墽琛屾垚鍔熶絾鎶ュ憡鍚庡鐞嗗憡璀︹€濈殑鎯呭喌銆?
  const status = (task.status || "").toLowerCase();
  if (status !== "success") return false;
  if ((task.allure_exit_code ?? 0) !== 0) return true;
  const output = (task.allure_output || "").toLowerCase();
  return output.includes("failed") || output.includes("warning") || output.includes("warn");
}

function isSameDeviceRuntimeStatus(
  left?: DeviceRuntimeStatus | null,
  right?: DeviceRuntimeStatus | null
): boolean {
  return (
    (left?.device_serial || "") === (right?.device_serial || "") &&
    (left?.status || "") === (right?.status || "") &&
    (left?.task_id || null) === (right?.task_id || null) &&
    (left?.message || "") === (right?.message || "") &&
    (left?.updated_at || null) === (right?.updated_at || null)
  );
}

function isSameTaskHistoryList(left: TaskHistoryItem[], right: TaskHistoryItem[]): boolean {
  if (left.length !== right.length) return false;
  for (let i = 0; i < left.length; i += 1) {
    const a = left[i];
    const b = right[i];
    if (
      a.task_id !== b.task_id ||
      a.status !== b.status ||
      (a.start_time || "") !== (b.start_time || "") ||
      (a.end_time || "") !== (b.end_time || "") ||
      (a.pytest_exit_code ?? null) !== (b.pytest_exit_code ?? null) ||
      (a.allure_exit_code ?? null) !== (b.allure_exit_code ?? null) ||
      (a.error || "") !== (b.error || "") ||
      Boolean(a.has_report) !== Boolean(b.has_report) ||
      (a.report_url || "") !== (b.report_url || "") ||
      Boolean(a.has_report_data) !== Boolean(b.has_report_data)
    ) {
      return false;
    }
  }
  return true;
}

function isSameReportSummary(left?: TaskReportSummary, right?: TaskReportSummary): boolean {
  return (
    (left?.task_id || "") === (right?.task_id || "") &&
    (left?.session_start || "") === (right?.session_start || "") &&
    (left?.session_end || "") === (right?.session_end || "") &&
    (left?.total ?? 0) === (right?.total ?? 0) &&
    (left?.passed ?? 0) === (right?.passed ?? 0) &&
    (left?.failed ?? 0) === (right?.failed ?? 0) &&
    (left?.skipped ?? 0) === (right?.skipped ?? 0) &&
    (left?.total_duration ?? 0) === (right?.total_duration ?? 0) &&
    (left?.pass_rate ?? 0) === (right?.pass_rate ?? 0) &&
    (left?.updated_at || "") === (right?.updated_at || "")
  );
}

function isSameReportCases(left: TaskReportCase[], right: TaskReportCase[]): boolean {
  if (left.length !== right.length) return false;
  for (let i = 0; i < left.length; i += 1) {
    const a = left[i];
    const b = right[i];
    if (
      a.id !== b.id ||
      a.case_index !== b.case_index ||
      (a.node_id || "") !== (b.node_id || "") ||
      (a.name || "") !== (b.name || "") ||
      (a.status || "") !== (b.status || "") ||
      (a.duration ?? 0) !== (b.duration ?? 0) ||
      (a.app || "") !== (b.app || "") ||
      (a.screenshot_url || "") !== (b.screenshot_url || "") ||
      (a.video_url || "") !== (b.video_url || "") ||
      (a.error_message || "") !== (b.error_message || "")
    ) {
      return false;
    }
  }
  return true;
}

function isSameReportPagination(left: ReportPagination, right: ReportPagination): boolean {
  return left.page === right.page && left.page_size === right.page_size && left.total === right.total;
}

async function apiRequest<T>(path: string, body?: unknown): Promise<T> {
  // 缁熶竴灏佽 GET/POST 璇锋眰涓庨敊璇鐞嗛€昏緫銆?
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
  // 涓婚〉闈㈢粍浠讹細璐熻矗璁惧绠＄悊銆佷换鍔℃墽琛屻€佺粨鏋滀笌鎶ュ憡灞曠ず銆?
  const [msgApi, contextHolder] = message.useMessage();
  const [activeTab, setActiveTab] = useState("devices");
  const [devices, setDevices] = useState<Device[]>([]);
  const [apps, setApps] = useState<AppOption[]>([]);
  const [packages, setPackages] = useState<TestPackageOption[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>();
  const [selectedApp, setSelectedApp] = useState<string>();
  const [selectedPackage, setSelectedPackage] = useState<string>();
  const [suite, setSuite] = useState("all");
  const [executionPackages, setExecutionPackages] = useState<string[]>([]);
  const [selectedExecutionIndex, setSelectedExecutionIndex] = useState<number>(-1);
  const [logText, setLogText] = useState("绛夊緟鎵ц...");
  const [startupMissing, setStartupMissing] = useState<string[]>([]);
  const [startupReady, setStartupReady] = useState(false);
  const [deviceRuntimeMap, setDeviceRuntimeMap] = useState<Record<string, DeviceRuntimeStatus>>({});
  const [currentTaskId, setCurrentTaskId] = useState<string>();
  const [taskHistory, setTaskHistory] = useState<TaskHistoryItem[]>([]);
  const [historyStatusFilter, setHistoryStatusFilter] = useState<string>("all");
  const [reportTaskId, setReportTaskId] = useState<string>();
  const [reportSummary, setReportSummary] = useState<TaskReportSummary>();
  const [reportCases, setReportCases] = useState<TaskReportCase[]>([]);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportCaseStatusFilter, setReportCaseStatusFilter] = useState<string>("all");
  const [reportPage, setReportPage] = useState(1);
  const [reportPageSize, setReportPageSize] = useState(10);
  const [reportPagination, setReportPagination] = useState<ReportPagination>({
    page: 1,
    page_size: 10,
    total: 0,
  });
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
  const packageLabelMap = useMemo(() => {
    const map: Record<string, string> = {};
    for (const item of packages) {
      const value = normalizePackageValue(item.value);
      if (!value) continue;
      const label = (item.label || "").trim();
      map[value] = label || fallbackPackageLabel(value);
    }
    return map;
  }, [packages]);
  const shouldPollTaskStatus = activeTab === "results" && Boolean(currentTaskId);
  const shouldPollTaskHistory = shouldPollTaskStatus;
  const shouldPollDeviceStatus =
    Boolean(selectedDevice) &&
    (activeTab === "devices" || activeTab === "runner" || shouldPollTaskStatus);
  const shouldLoadReportData = activeTab === "report" && Boolean(reportTaskId);
  const tabItems = useMemo(
    () => [
      { key: "devices", label: "手机终端" },
      { key: "runner", label: "用例执行" },
      { key: "results", label: "执行结果" },
      { key: "report", label: "测试报告" },
    ],
    []
  );
  const deviceSelectOptions = useMemo(
    () => devices.map((d) => ({ value: d.serial, label: `${d.serial} (${formatDeviceStatus(d.status)})` })),
    [devices]
  );
  const appSelectOptions = useMemo(
    () => apps.map((a) => ({ value: a.key, label: a.label })),
    [apps]
  );
  const packageSelectOptions = useMemo(
    () =>
      packages.map((item) => ({
        value: item.value,
        label: item.label,
        title: item.tooltip || item.label,
      })),
    [packages]
  );
  const suiteOptions = useMemo(
    () => [
      { value: "all", label: "全部" },
      { value: "smoke", label: "冒烟测试" },
      { value: "full", label: "全量测试" },
    ],
    []
  );
  const historyStatusOptions = useMemo(
    () => [
      { value: "all", label: "全部状态" },
      { value: "running", label: "运行中" },
      { value: "success", label: "成功" },
      { value: "failed", label: "失败" },
      { value: "stopped", label: "已停止" },
      { value: "report_warning", label: "仅报告告警" },
    ],
    []
  );
  const reportCaseStatusOptions = useMemo(
    () => [
      { value: "all", label: "全部状态" },
      { value: "passed", label: "通过" },
      { value: "failed", label: "失败" },
      { value: "skipped", label: "跳过" },
    ],
    []
  );
  const deviceTableColumns = useMemo(
    () => [
      { title: "设备序列号", dataIndex: "serial" },
      { title: "状态", render: (_: unknown, d: Device) => formatDeviceStatus(d.status) },
      { title: "任务状态", render: (_: unknown, d: Device) => formatRunStatus(deviceRuntimeMap[d.serial]?.status) },
      { title: "品牌", render: (_: unknown, d: Device) => renderBrand(d.brand, 32) },
      { title: "型号", dataIndex: "model" },
      { title: "系统", dataIndex: "os_version" },
      {
        title: "鎼存梻鏁ら悧鍫熸拱",
        render: (_: unknown, d: Device) =>
          `Lysora: ${(d.app_versions && d.app_versions.lysora) || "-"} / Ruijie: ${
            (d.app_versions && d.app_versions.ruijieCloud) || "-"
          }`,
      },
    ],
    [deviceRuntimeMap]
  );
  const reportTablePagination = useMemo(
    () => ({
      current: reportPagination.page,
      pageSize: reportPagination.page_size,
      total: reportPagination.total,
      hideOnSinglePage: reportPagination.total <= reportPagination.page_size,
      onChange: (page: number, pageSize: number) => {
        setReportPage(page);
        setReportPageSize(pageSize);
      },
    }),
    [reportPagination.page, reportPagination.page_size, reportPagination.total]
  );
  const resultsTableColumns = useMemo(
    () => [
      { title: "任务ID", dataIndex: "task_id", width: 130 },
      { title: "设备", dataIndex: "device_serial", width: 140 },
      {
        title: "状态",
        render: (_: unknown, r: TaskHistoryItem) => {
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
      { title: "Pytest结果", render: (_: unknown, r: TaskHistoryItem) => formatExitCode(r.pytest_exit_code), width: 120 },
      { title: "报告结果", render: (_: unknown, r: TaskHistoryItem) => formatExitCode(r.allure_exit_code), width: 120 },
      {
        title: "操作",
        width: 180,
        render: (_: unknown, r: TaskHistoryItem) => (
          <Space size={6}>
            <Button
              size="small"
              disabled={!r.has_report}
              onClick={(ev) => {
                ev.stopPropagation();
                if (!r.has_report) return;
                const url = r.report_url || "/api/task_report/" + encodeURIComponent(r.task_id);
                window.open(url, "_blank");
              }}
            >
              查看报告
            </Button>
            <Button
              size="small"
              onClick={(ev) => {
                ev.stopPropagation();
                window.open("/api/task_log/" + encodeURIComponent(r.task_id), "_blank");
              }}
            >
              下载日志
            </Button>
          </Space>
        ),
      },
    ],
    []
  );

  const reportCaseColumns = useMemo(
    () => [
      { title: "#", dataIndex: "case_index", width: 50 },
      { title: "测试用例", dataIndex: "name", ellipsis: true },
      {
        title: "状态",
        width: 90,
        render: (_: unknown, r: TaskReportCase) => {
          const s = (r.status || "").toLowerCase();
          const color = s === "passed" ? "green" : s === "failed" ? "red" : s === "skipped" ? "orange" : "default";
          return <Tag color={color}>{formatCaseStatus(r.status)}</Tag>;
        },
      },
      {
        title: "耗时",
        width: 90,
        render: (_: unknown, r: TaskReportCase) => (r.duration || 0).toFixed(2) + "s",
      },
      { title: "应用", dataIndex: "app", width: 100 },
    ],
    []
  );



  const refreshDeviceRuntime = async (deviceSerial: string) => {
    // 鍒锋柊鍗曚釜璁惧鐨勫疄鏃朵换鍔＄姸鎬佸苟鏇存柊缂撳瓨銆?
    const res = await apiRequest<{ ok: boolean; device_status: DeviceRuntimeStatus }>(
      `/api/device_status/${encodeURIComponent(deviceSerial)}`
    );
    if (res.ok && res.device_status) {
      setDeviceRuntimeMap((old) => {
        if (isSameDeviceRuntimeStatus(old[deviceSerial], res.device_status)) {
          return old;
        }
        return { ...old, [deviceSerial]: res.device_status };
      });
      return res.device_status;
    }
    return null;
  };

  const refreshTaskHistory = async () => {
    // 鎸夊綋鍓嶇瓫閫夋潯浠舵媺鍙栦换鍔″巻鍙诧紝骞跺悓姝ュ彲閫夋姤鍛婁换鍔°€?
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
      setTaskHistory((old) => (isSameTaskHistoryList(old, list) ? old : list));
      setReportTaskId((old) => {
        if (old && list.some((t) => t.task_id === old && t.has_report_data)) return old;
        return list.find((t) => t.has_report_data)?.task_id;
      });
    }
  };

  const refreshTaskReportData = async (taskId?: string) => {
    // 鎷夊彇骞舵洿鏂颁换鍔℃姤鍛婃憳瑕佷笌鐢ㄤ緥鏄庣粏銆?
    const targetTaskId = taskId || reportTaskId;
    if (!targetTaskId) {
      setReportSummary((old) => (old === undefined ? old : undefined));
      setReportCases((old) => (old.length === 0 ? old : []));
      setReportPagination((old) => {
        const next = { page: 1, page_size: reportPageSize, total: 0 };
        return isSameReportPagination(old, next) ? old : next;
      });
      return;
    }
    setReportLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(reportPage));
      params.set("page_size", String(reportPageSize));
      if (reportCaseStatusFilter !== "all") {
        params.set("status", reportCaseStatusFilter);
      }
      const res = await apiRequest<
        ApiOk & {
          task_id: string;
          summary: TaskReportSummary;
          tests: TaskReportCase[];
          pagination?: ReportPagination;
        }
      >(`/api/task_report_data/${encodeURIComponent(targetTaskId)}?${params.toString()}`);
      if (!res.ok) {
        setReportSummary((old) => (old === undefined ? old : undefined));
        setReportCases((old) => (old.length === 0 ? old : []));
        setReportPagination((old) => {
          const next = { page: 1, page_size: reportPageSize, total: 0 };
          return isSameReportPagination(old, next) ? old : next;
        });
        return;
      }
      const nextSummary = res.summary;
      const nextCases = res.tests || [];
      const nextPagination =
        res.pagination || {
          page: reportPage,
          page_size: reportPageSize,
          total: res.tests?.length || 0,
        };
      setReportSummary((old) => (isSameReportSummary(old, nextSummary) ? old : nextSummary));
      setReportCases((old) => (isSameReportCases(old, nextCases) ? old : nextCases));
      setReportPagination((old) => (isSameReportPagination(old, nextPagination) ? old : nextPagination));
    } catch (err) {
      setReportSummary((old) => (old === undefined ? old : undefined));
      setReportCases((old) => (old.length === 0 ? old : []));
      msgApi.error(`鍔犺浇浠诲姟鎶ュ憡澶辫触: ${String(err)}`);
    } finally {
      setReportLoading(false);
    }
  };

  const refreshDevices = async () => {
    // 鍒锋柊璁惧鍒楄〃锛屽悓鏃惰ˉ榻愭瘡鍙拌澶囩殑杩愯鐘舵€併€?
    setLogText("姝ｅ湪鍒锋柊璁惧...");
    const res = await apiRequest<{ ok: boolean; devices: Device[]; error?: string }>(
      "/api/list_devices",
      {}
    );
    if (!res.ok) {
      setLogText(`鍒锋柊璁惧澶辫触:\n${res.error || "unknown error"}`);
      return;
    }
    const list = res.devices || [];
    setDevices(list);
    const nextRuntimeMap: Record<string, DeviceRuntimeStatus> = {};
    for (const d of list) {
      nextRuntimeMap[d.serial] = d.runtime_status || {
        device_serial: d.serial,
        status: "idle",
        task_id: null,
        message: "",
        updated_at: null,
      };
    }
    setDeviceRuntimeMap(nextRuntimeMap);
    if (list.length > 0) {
      setSelectedDevice((old) => old && list.some((d) => d.serial === old) ? old : list[0].serial);
    } else {
      setSelectedDevice(undefined);
      setDeviceRuntimeMap({});
      setLogText("未找到可用设备，请检查 adb devices。");
    }
  };

  const refreshApps = async () => {
    // 鑾峰彇搴旂敤閫夐」骞舵牎姝ｅ綋鍓嶉€変腑椤广€?
    const res = await apiRequest<AppOption[]>("/api/get_app_options");
    setApps(res || []);
    if (res?.length) {
      setSelectedApp((old) => old && res.some((a) => a.key === old) ? old : res[0].key);
    }
  };

  const refreshPackages = async (appKey?: string) => {
    // 鏍规嵁搴旂敤鍒锋柊鍙墽琛岀敤渚嬪寘锛屽苟缁存姢鎵ц闃熷垪閫夋嫨鐘舵€併€?
    const targetApp = appKey || selectedApp;
    if (!targetApp) return;
    const res = await apiRequest<{
      ok: boolean;
      packages: Array<string | TestPackageOption>;
      package_paths?: string[];
      error?: string;
    }>(
      "/api/list_test_packages",
      { app_key: targetApp }
    );
    if (!res.ok) {
      setLogText(`加载用例包失败\n${res.error || "unknown error"}`);
      return;
    }
    const rawList = Array.isArray(res.packages) ? res.packages : [];
    const list: TestPackageOption[] = rawList
      .map((entry) => {
        if (typeof entry === "string") {
          return { value: entry, label: entry };
        }
        const value = String(entry?.value || "").trim();
        if (!value) return null;
        const label = String(entry?.label || value).trim() || value;
        const tooltip = String(entry?.tooltip || "").trim();
        return { value, label, tooltip: tooltip || label };
      })
      .filter((item): item is TestPackageOption => Boolean(item));
    setPackages(list);
    const values = list.map((item) => item.value);
    setSelectedPackage((old) => {
      const normalized = normalizePackageValue(old);
      return normalized && values.includes(normalized) ? normalized : values[0];
    });
    setExecutionPackages((old) => {
      const filtered = normalizePackageQueue(old).filter((p) => values.includes(p));
      return filtered.length ? filtered : (values[0] ? [values[0]] : []);
    });
    setSelectedExecutionIndex((old) => (old >= 0 ? old : (list.length ? 0 : -1)));
    setLogText("用例包已刷新。");
  };

  const addSelectedCase = () => {
    // 灏嗗綋鍓嶉€変腑鐨勭敤渚嬪寘鍔犲叆寰呮墽琛屽垪琛紙閬垮厤閲嶅锛夈€?
    const selectedValue = normalizePackageValue(selectedPackage);
    if (!selectedValue) return;
    if (executionPackages.includes(selectedValue)) {
      msgApi.info("该用例已在待执行列表中");
      setSelectedExecutionIndex(executionPackages.indexOf(selectedValue));
      return;
    }
    const next = normalizePackageQueue([...executionPackages, selectedValue]);
    setExecutionPackages(next);
    setSelectedExecutionIndex(next.length - 1);
  };

  const addAllCases = () => {
    // 鎵归噺灏嗗彲閫夌敤渚嬪姞鍏ュ緟鎵ц鍒楄〃锛岃嚜鍔ㄨ烦杩囬噸澶嶉」銆?
    let added = 0;
    let skipped = 0;
    const next = normalizePackageQueue(executionPackages);
    for (const p of packages) {
      if (next.includes(p.value)) {
        skipped += 1;
      } else {
        next.push(p.value);
        added += 1;
      }
    }
    setExecutionPackages(next);
    if (next.length) setSelectedExecutionIndex(next.length - 1);
    msgApi.info(`批量添加完成：新增 ${added}，跳过重复 ${skipped}`);
  };

  const removeSelectedCase = () => {
    // 绉婚櫎褰撳墠楂樹寒閫変腑鐨勫緟鎵ц鐢ㄤ緥銆?
    if (selectedExecutionIndex < 0 || selectedExecutionIndex >= executionPackages.length) return;
    const next = executionPackages.filter((_, idx) => idx !== selectedExecutionIndex);
    setExecutionPackages(normalizePackageQueue(next));
    setSelectedExecutionIndex(Math.min(selectedExecutionIndex, next.length - 1));
  };

  const moveSelectedCase = (offset: number) => {
    // 鎸夌粰瀹氬亸绉婚噺璋冩暣寰呮墽琛岀敤渚嬮『搴忋€?
    const from = selectedExecutionIndex;
    const to = from + offset;
    if (from < 0 || from >= executionPackages.length) return;
    if (to < 0 || to >= executionPackages.length) return;
    const next = normalizePackageQueue(executionPackages);
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    setExecutionPackages(normalizePackageQueue(next));
    setSelectedExecutionIndex(to);
  };

  const runTests = async () => {
    // 鏍￠獙鎵ц鍓嶆彁骞跺垱寤烘祴璇曚换鍔°€?
    try {
      const appium = await apiRequest<{ running: boolean; server_url?: string; error?: string }>(
        "/api/appium_ready"
      );
      if (!appium.running) {
        const addr = appium.server_url || "http://127.0.0.1:4723";
        msgApi.error(`Appium 未启动（${addr}）`);
        setLogText(`鎵ц宸插彇娑堬細Appium 鏈惎鍔╘n鍦板潃: ${addr}\n璇︽儏: ${appium.error || "unknown error"}`);
        setActiveTab("results");
        return;
      }
      if (!executionPackages.length) {
        msgApi.error("璇峰厛娣诲姞鑷冲皯涓€涓緟鎵ц鐢ㄤ緥");
        return;
      }
      if (!selectedDevice) {
        msgApi.error("璇峰厛閫夋嫨鎵嬫満璁惧");
        return;
      }
      if (!selectedApp) {
        msgApi.error("璇峰厛閫夋嫨搴旂敤");
        return;
      }
      if (isSelectedDeviceRunning) {
        msgApi.warning("璇ユ墜鏈哄凡鏈変换鍔″湪杩愯涓紝涓嶈兘閲嶅鍚姩");
        return;
      }

      setActiveTab("results");
      setLogText(
        `姝ｅ湪鎵ц娴嬭瘯锛岃绋嶅€?..\n鎵ц椤哄簭:\n${executionPackages
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
        setLogText(`鎵ц澶辫触\n\n${res.error || "unknown error"}`);
        return;
      }
      if (res.task_id) {
        setCurrentTaskId(res.task_id);
        await refreshDeviceRuntime(selectedDevice);
        await refreshTaskHistory();
        msgApi.success(`任务已启动: ${res.task_id}`);
        setLogText((old) => `${old}\n\n浠诲姟宸插垱寤? ${res.task_id}`);
      }
    } catch (err) {
      msgApi.error("鍚姩浠诲姟澶辫触");
      setLogText(`鎵ц澶辫触\n\n${String(err)}`);
    }
  };

  const stopCurrentTask = async () => {
    // 璇锋眰鍚庣鍋滄褰撳墠璁惧涓婄殑浠诲姟锛屽苟鍒锋柊鐘舵€併€?
    if (!selectedDevice) return;
    const res = await apiRequest<ApiOk & { task_id?: string; status?: string }>(
      "/api/stop_task",
      {
        task_id: currentTaskId,
        device: selectedDevice,
      }
    );
    if (!res.ok) {
      msgApi.error(res.error || "鍋滄浠诲姟澶辫触");
      return;
    }
    msgApi.info("停止请求已发送");
    await refreshDeviceRuntime(selectedDevice);
    await refreshTaskHistory();
  };

  const openReport = async () => {
    // 鎵撳紑鏈€杩戜竴娆＄敓鎴愮殑娴嬭瘯鎶ュ憡銆?
    const res = await apiRequest<ApiOk>("/api/open_report", {});
    if (!res.ok) {
      msgApi.error(res.error || "鎵撳紑鎶ュ憡澶辫触");
    }
  };

  const refreshSelectedDeviceStatus = async () => {
    // 鎵嬪姩鍒锋柊褰撳墠閫変腑璁惧鐘舵€侊紝骞跺悓姝ュ綋鍓嶄换鍔?ID銆?
    if (!selectedDevice) {
      msgApi.warning("璇峰厛閫夋嫨鎵嬫満璁惧");
      return;
    }
    const s = await refreshDeviceRuntime(selectedDevice);
    if (s?.status === "running" && s.task_id) {
      setCurrentTaskId((old) => old || s.task_id || undefined);
    } else if (s && s.status !== "running") {
      setCurrentTaskId(undefined);
    }
  };

  const refreshCurrentTaskStatus = async (options?: { silent?: boolean }) => {
    const silent = Boolean(options?.silent);
    // 鎷夊彇褰撳墠浠诲姟鐘舵€佷笌鏃ュ織杈撳嚭锛屽苟鍦ㄧ粨鏉熷悗鍋氭敹灏惧埛鏂般€?
    if (!currentTaskId) {
      if (silent) {
        return;
      }
      msgApi.warning("褰撳墠娌℃湁鍙埛鏂扮殑浠诲姟");
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
        `浠诲姟: ${res.task_id}\n鐘舵€? ${formatRunStatus(res.status)}\nPytest缁撴灉: ${formatExitCode(
          res.pytest_exit_code
        )}\n鎶ュ憡缁撴灉: ${formatExitCode(res.allure_exit_code)}\n\n${res.pytest_output || ""}\n\n--- 鎶ュ憡杈撳嚭 ---\n${
          res.allure_output || ""
        }${res.error ? `\n\n閿欒: ${res.error}` : ""}`
      );
      if (res.status && ["success", "failed", "stopped"].includes(res.status)) {
        setCurrentTaskId(undefined);
        if (selectedDevice) await refreshDeviceRuntime(selectedDevice);
        await refreshTaskHistory();
        msgApi.info(`任务已结束: ${res.status}`);
      }
    } catch {
      if (silent) {
        return;
      }
      msgApi.error("刷新任务状态失败");
    }
  };

  useEffect(() => {
    // 椤甸潰棣栨鍔犺浇锛氭媺鍙栧惎鍔ㄤ緷璧栦俊鎭€佸簲鐢ㄣ€佽澶囦笌鍘嗗彶鏁版嵁銆?
    (async () => {
      try {
        const startup = await apiRequest<{ missing_dependencies?: string[] }>("/api/startup_info");
        setStartupMissing(startup.missing_dependencies || []);
        await Promise.all([refreshApps(), refreshDevices()]);
      } catch (err) {
        setLogText(`页面初始化失败\n${String(err)}`);
      }
      setStartupReady(true);
    })();
  }, []);

  useEffect(() => {
    // 搴旂敤鍒囨崲鍚庯紝鑷姩鍒锋柊瀵瑰簲鐨勭敤渚嬪寘銆?
    if (selectedApp) {
      refreshPackages(selectedApp);
    }
  }, [selectedApp]);

  useEffect(() => {
    setReportPage(1);
  }, [reportTaskId, reportCaseStatusFilter]);

  useEffect(() => {
    // 璁惧鎴栧巻鍙茬瓫閫夊彉鏇村悗锛岃嚜鍔ㄥ埛鏂颁换鍔″巻鍙层€?
    if (!startupReady) return;
    refreshTaskHistory();
  }, [historyStatusFilter, selectedDevice, startupReady]);

  useEffect(() => {
    // 璁惧鍒囨崲鍚庯紝鑷姩鍒锋柊璁惧鐘舵€佸苟鎭㈠杩愯涓殑浠诲姟涓婁笅鏂囥€?
    if (!selectedDevice) return;
    refreshDeviceRuntime(selectedDevice).then((s) => {
      if (s?.status === "running" && s.task_id) {
        setCurrentTaskId(s.task_id);
      }
    });
  }, [selectedDevice]);

  useEffect(() => {
    if (!selectedDevice) return;
    if (!shouldPollDeviceStatus) return;
    const timer = window.setInterval(() => {
      void refreshDeviceRuntime(selectedDevice);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [selectedDevice, shouldPollDeviceStatus]);

  useEffect(() => {
    // 鏈夊綋鍓嶄换鍔℃椂锛岃嚜鍔ㄨЕ鍙戜竴娆′换鍔＄姸鎬佸埛鏂般€?
    if (!shouldPollTaskStatus) return;
    void refreshCurrentTaskStatus({ silent: true });
    const timer = window.setInterval(() => {
      void refreshCurrentTaskStatus({ silent: true });
    }, 3000);
    return () => window.clearInterval(timer);
  }, [currentTaskId, shouldPollTaskStatus]);

  useEffect(() => {
    // 娴犲懎婀紒鎾寸亯妞ゅ吀绗栫€涙ê婀潻鎰攽娴犺濮熼弮璁圭礉閹靛秴鎳嗛張鐔糕偓褍鍩涢弬鏉垮坊閸欐彃鍨悰顭掔礉闁灝鍘ら崗鏈电铂妞ょ敻娼伴惃鍕￥閺佸牐顕Ч鍌樷偓?
    if (!shouldPollTaskHistory) return;
    const timer = window.setInterval(() => {
      void refreshTaskHistory();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [historyStatusFilter, shouldPollTaskHistory]);

  useEffect(() => {
    // 鎶ュ憡浠诲姟鍒囨崲鍚庯紝鑷姩鍔犺浇瀵瑰簲鎶ュ憡鏁版嵁銆?
    if (!shouldLoadReportData || !reportTaskId) return;
    refreshTaskReportData(reportTaskId);
  }, [reportCaseStatusFilter, reportPage, reportPageSize, reportTaskId, shouldLoadReportData]);

  return (
    <div style={{ width: "calc(100% - 24px)", maxWidth: "none", margin: "8px 12px 16px", padding: 0 }}>
      {contextHolder}
      <Typography.Title level={3} style={{ marginTop: 4 }}>
        绉诲姩鑷姩鍖栨祴璇曟闈㈢
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
            { key: "devices", label: "鎵嬫満缁堢" },
            { key: "runner", label: "鐢ㄤ緥鎵ц" },
            { key: "results", label: "鎵ц缁撴灉" },
            { key: "report", label: "娴嬭瘯鎶ュ憡" },
          ]}
        />
      </Card>

      {activeTab === "devices" && (
        <Card title="当前连接的手机终端">
          <Space style={{ marginBottom: 12 }}>
            <Button onClick={refreshDevices}>鍒锋柊璁惧</Button>
          </Space>
          <Table<Device>
            rowKey="serial"
            pagination={false}
            dataSource={devices}
            columns={deviceTableColumns}
          />
        </Card>
      )}

      {activeTab === "runner" && (
        <Card title="閫夋嫨缁堢銆佹祴璇曠敤渚嬪苟鎵ц">
          <Row gutter={[12, 12]}>
            <Col span={6}>
              <label>鎵嬫満璁惧</label>
              <Select
                style={{ width: "100%" }}
                value={selectedDevice}
                onChange={setSelectedDevice}
                options={deviceSelectOptions}
              />
            </Col>
            <Col span={6}>
              <label>搴旂敤</label>
              <Select
                style={{ width: "100%" }}
                value={selectedApp}
                onChange={setSelectedApp}
                options={appSelectOptions}
              />
            </Col>
            <Col span={6}>
              <label>可选用例</label>
              <Select
                style={{ width: "100%" }}
                value={selectedPackage}
                onChange={(value) => setSelectedPackage(normalizePackageValue(value))}
                options={packageSelectOptions}
              />
            </Col>
            <Col span={6}>
              <label>测试范围</label>
              <Select
                style={{ width: "100%" }}
                value={suite}
                onChange={setSuite}
                options={suiteOptions}
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
              鍚姩鎵ц
            </Button>
            <Button htmlType="button" danger onClick={stopCurrentTask} disabled={!isSelectedDeviceRunning}>
              鍋滄浠诲姟
            </Button>
          </Space>

          <Card
            size="small"
            style={{ marginTop: 12, background: "#fafafa" }}
            title="寰呮墽琛岀敤渚嬶紙鎸夊垪琛ㄩ『搴忔墽琛岋級"
            extra={
              <Space wrap>
                <Button size="small" onClick={addSelectedCase}>
                  娣诲姞
                </Button>
                <Button size="small" onClick={addAllCases}>
                  娣诲姞鍏ㄩ儴
                </Button>
                <Button size="small" onClick={removeSelectedCase}>
                  绉婚櫎
                </Button>
                <Button size="small" onClick={() => moveSelectedCase(-1)}>
                  涓婄Щ
                </Button>
                <Button size="small" onClick={() => moveSelectedCase(1)}>
                  涓嬬Щ
                </Button>
                <Button
                  size="small"
                  onClick={() => {
                    setExecutionPackages([]);
                    setSelectedExecutionIndex(-1);
                  }}
                >
                  娓呯┖
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
                  {idx + 1}. {resolvePackageLabel(item, packageLabelMap)}
                </List.Item>
              )}
            />
          </Card>

          <Row gutter={10} style={{ marginTop: 12 }}>
            <Col span={5}>
              <Card size="small" title="鎵嬫満鍝佺墝" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                {renderBrand(currentDevice?.brand, 56)}
              </Card>
            </Col>
            <Col span={5}>
              <Card size="small" title="璁惧鍨嬪彿" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                <span style={summaryValueStyle}>{currentDevice?.model || "-"}</span>
              </Card>
            </Col>
            <Col span={5}>
              <Card size="small" title="绯荤粺鐗堟湰" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                <span style={summaryValueStyle}>{currentDevice?.os_version || "-"}</span>
              </Card>
            </Col>
            <Col span={4}>
              <Card size="small" title="Lysora 鐗堟湰" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                <span style={summaryValueStyle}>
                  {(currentDevice?.app_versions && currentDevice.app_versions.lysora) || "-"}
                </span>
              </Card>
            </Col>
            <Col span={5}>
              <Card size="small" title="ruijieCloud 鐗堟湰" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
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
          title="娴嬭瘯鐢ㄤ緥缁撴灉"
          extra={
            <Space>
              <Select
                style={{ width: 150 }}
                value={historyStatusFilter}
                onChange={setHistoryStatusFilter}
                options={historyStatusOptions}
              />
              <Button onClick={refreshTaskHistory}>刷新历史</Button>
              <Button onClick={() => void refreshCurrentTaskStatus()} disabled={!currentTaskId}>
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
            columns={resultsTableColumns}
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
          title="娴嬭瘯鎶ュ憡"
          extra={
            <Space wrap>
              <Select
                style={{ width: 340 }}
                placeholder="閫夋嫨浠诲姟"
                value={reportTaskId}
                onChange={(v) => setReportTaskId(v)}
                options={reportTasks}
              />
              <Select
                style={{ width: 120 }}
                value={reportCaseStatusFilter}
                onChange={(value) => {
                  setReportCaseStatusFilter(value);
                  setReportPage(1);
                }}
                options={reportCaseStatusOptions}
              />
              <Button onClick={() => refreshTaskReportData()}>鍒锋柊鎶ュ憡</Button>
              <Button
                disabled={!selectedReportTask?.has_report}
                onClick={() => {
                  if (!selectedReportTask?.has_report) return;
                  const url = selectedReportTask.report_url || "/api/task_report/" + encodeURIComponent(selectedReportTask.task_id);
                  window.open(url, "_blank");
                }}
              >
                鎵撳紑HTML鎶ュ憡
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
                <Card size="small" title="鎬昏">
                  <Typography.Title level={4} style={{ margin: 0 }}>{reportSummary.total}</Typography.Title>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small" title="閫氳繃">
                  <Typography.Title level={4} style={{ margin: 0, color: "#16a34a" }}>{reportSummary.passed}</Typography.Title>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small" title="澶辫触">
                  <Typography.Title level={4} style={{ margin: 0, color: "#dc2626" }}>{reportSummary.failed}</Typography.Title>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small" title="璺宠繃">
                  <Typography.Title level={4} style={{ margin: 0, color: "#d97706" }}>{reportSummary.skipped}</Typography.Title>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small" title="通过率">
                  <Typography.Title level={4} style={{ margin: 0 }}>{(reportSummary.pass_rate || 0).toFixed(1)}%</Typography.Title>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small" title="鎬昏€楁椂">
                  <Typography.Title level={4} style={{ margin: 0 }}>{(reportSummary.total_duration || 0).toFixed(1)}s</Typography.Title>
                </Card>
              </Col>
            </Row>
          )}
          <Table<TaskReportCase>
            rowKey={(r) => r.task_id + "-" + r.case_index}
            size="small"
            loading={reportLoading}
            pagination={reportTablePagination}
            dataSource={reportCases}
            expandable={{
              expandedRowRender: (record) => (
                <div>
                  <div><b>鑺傜偣:</b> {record.node_id || "-"}</div>
                  <div style={{ marginTop: 6 }}>
                    <b>閿欒:</b> {record.error_message || "-"}
                  </div>
                  <Space style={{ marginTop: 8 }}>
                    <Button
                      size="small"
                      disabled={!record.screenshot_url}
                      onClick={() => record.screenshot_url && window.open(record.screenshot_url, "_blank")}
                    >
                      鏌ョ湅鎴浘
                    </Button>
                    <Button
                      size="small"
                      disabled={!record.video_url}
                      onClick={() => record.video_url && window.open(record.video_url, "_blank")}
                    >
                      鏌ョ湅瑙嗛
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
            columns={reportCaseColumns}
          />
        </Card>
      )}
    </div>
  );
}

export default App;









