import { useEffect, useMemo, useState } from "react";
import { Button, Card, message, Select, Space, Tabs, Typography, Tag } from "antd";
import type { CSSProperties } from "react";
import {
  fallbackPackageLabel,
  formatCaseStatus,
  formatDeviceStatus,
  formatExitCode,
  formatRunStatus,
  hasReportWarning,
  isSameDeviceRuntimeStatus,
  isSameReportCases,
  isSameReportPagination,
  isSameReportSummary,
  isSameTaskHistoryList,
  normalizePackageQueue,
  normalizePackageValue,
  renderBrand,
} from "./lib/appHelpers";
import {
  getAppOptions,
  getAppiumReady,
  getDeviceRuntime,
  getStartupInfo,
  getTaskHistory,
  getTaskReportData,
  getTaskStatus,
  listDevices,
  listTestPackages,
  openReport as openReportRequest,
  runTests as runTestsRequest,
  stopTask,
} from "./lib/api";
import type {
  AppOption,
  Device,
  DeviceRuntimeStatus,
  ReportPagination,
  TaskHistoryItem,
  TaskReportCase,
  TaskReportSummary,
  TestPackageOption,
} from "./types/app";
import DevicesTab from "./components/DevicesTab";
import ReportTab from "./components/ReportTab";
import ResultsTab from "./components/ResultsTab";
import RunnerTab from "./components/RunnerTab";
import StartupAlert from "./components/StartupAlert";

function App() {
  // 主页面组件：负责设备管理、任务执行、结果与报告展示。
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
  const [logText, setLogText] = useState("等待执行...");
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
        title: "应用版本",
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
    // 刷新单个设备的实时任务状态并更新缓存。
    const res = await getDeviceRuntime(deviceSerial);
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
    // 按当前筛选条件拉取任务历史，并同步可选报告任务。
    const res = await getTaskHistory({
      limit: 30,
      device: selectedDevice,
      status: historyStatusFilter !== "all" && historyStatusFilter !== "report_warning" ? historyStatusFilter : undefined,
    });
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
    // 拉取并更新任务报告摘要与用例明细。
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
      const res = await getTaskReportData({
      taskId: targetTaskId,
      page: reportPage,
      pageSize: reportPageSize,
      status: reportCaseStatusFilter !== "all" ? reportCaseStatusFilter : undefined,
    });
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
      msgApi.error(`加载任务报告失败: ${String(err)}`);
    } finally {
      setReportLoading(false);
    }
  };

  const refreshDevices = async () => {
    // 刷新设备列表，同时补齐每台设备的运行状态。
    setLogText("正在刷新设备...");
    const res = await listDevices();
    if (!res.ok) {
      setLogText(`刷新设备失败:\n${res.error || "unknown error"}`);
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
    // 获取应用选项并校正当前选中项。
    const res = await getAppOptions();
    setApps(res || []);
    if (res?.length) {
      setSelectedApp((old) => old && res.some((a) => a.key === old) ? old : res[0].key);
    }
  };

  const refreshPackages = async (appKey?: string) => {
    // 根据应用刷新可执行用例包，并维护执行队列选择状态。
    const targetApp = appKey || selectedApp;
    if (!targetApp) return;
    const res = await listTestPackages(targetApp);
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
    // 将当前选中的用例包加入待执行列表，避免重复。
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
    // 批量将可选用例加入待执行列表，自动跳过重复项。
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
    // 移除当前高亮选中的待执行用例。
    if (selectedExecutionIndex < 0 || selectedExecutionIndex >= executionPackages.length) return;
    const next = executionPackages.filter((_, idx) => idx !== selectedExecutionIndex);
    setExecutionPackages(normalizePackageQueue(next));
    setSelectedExecutionIndex(Math.min(selectedExecutionIndex, next.length - 1));
  };

  const moveSelectedCase = (offset: number) => {
    // 按给定偏移量调整待执行用例顺序。
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
    // 校验执行前提并创建测试任务。
    try {
      const appium = await getAppiumReady();
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
      const res = await runTestsRequest({
        device: selectedDevice,
        app_key: selectedApp,
        test_packages: executionPackages,
        suite,
      });
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
    // 请求后端停止当前设备上的任务，并刷新状态。
    if (!selectedDevice) return;
    const res = await stopTask({
      task_id: currentTaskId,
      device: selectedDevice,
    });
    if (!res.ok) {
      msgApi.error(res.error || "停止任务失败");
      return;
    }
    msgApi.info("停止请求已发送");
    await refreshDeviceRuntime(selectedDevice);
    await refreshTaskHistory();
  };

  const openReport = async () => {
    // 打开最近一次生成的测试报告。
    const res = await openReportRequest();
    if (!res.ok) {
      msgApi.error(res.error || "打开报告失败");
    }
  };

  const refreshSelectedDeviceStatus = async () => {
    // 手动刷新当前选中设备状态，并同步当前任务 ID。
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

  const refreshCurrentTaskStatus = async (options?: { silent?: boolean }) => {
    const silent = Boolean(options?.silent);
    // 拉取当前任务状态与日志输出，并在结束后做收尾刷新。
    if (!currentTaskId) {
      if (silent) {
        return;
      }
      msgApi.warning("当前没有可刷新的任务");
      return;
    }
    try {
      const res = await getTaskStatus(currentTaskId);
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
      if (silent) {
        return;
      }
      msgApi.error("刷新任务状态失败");
    }
  };

  useEffect(() => {
    // 页面首次加载：拉取启动依赖信息、应用、设备与历史数据。
    (async () => {
      try {
        const startup = await getStartupInfo();
        setStartupMissing(startup.missing_dependencies || []);
        await Promise.all([refreshApps(), refreshDevices()]);
      } catch (err) {
        setLogText(`页面初始化失败\n${String(err)}`);
      }
      setStartupReady(true);
    })();
  }, []);

  useEffect(() => {
    // 应用切换后，自动刷新对应的用例包。
    if (selectedApp) {
      refreshPackages(selectedApp);
    }
  }, [selectedApp]);

  useEffect(() => {
    setReportPage(1);
  }, [reportTaskId, reportCaseStatusFilter]);

  useEffect(() => {
    // 设备或历史筛选变化后，自动刷新任务历史。
    if (!startupReady) return;
    refreshTaskHistory();
  }, [historyStatusFilter, selectedDevice, startupReady]);

  useEffect(() => {
    // 设备切换后，自动刷新设备状态并恢复运行中的任务上下文。
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
    // 有当前任务时，自动触发一次任务状态刷新。
    if (!shouldPollTaskStatus) return;
    void refreshCurrentTaskStatus({ silent: true });
    const timer = window.setInterval(() => {
      void refreshCurrentTaskStatus({ silent: true });
    }, 3000);
    return () => window.clearInterval(timer);
  }, [currentTaskId, shouldPollTaskStatus]);

  useEffect(() => {
    // 结果页存在当前任务时，自动轮询任务历史。
    if (!shouldPollTaskHistory) return;
    const timer = window.setInterval(() => {
      void refreshTaskHistory();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [historyStatusFilter, shouldPollTaskHistory]);

  useEffect(() => {
    // 报告任务切换后，自动加载对应报告数据。
    if (!shouldLoadReportData || !reportTaskId) return;
    refreshTaskReportData(reportTaskId);
  }, [reportCaseStatusFilter, reportPage, reportPageSize, reportTaskId, shouldLoadReportData]);

  return (
    <div style={{ width: "calc(100% - 24px)", maxWidth: "none", margin: "8px 12px 16px", padding: 0 }}>
      {contextHolder}
      <Typography.Title level={3} style={{ marginTop: 4 }}>
        移动自动化测试桌面端
      </Typography.Title>

      <StartupAlert startupMissing={startupMissing} />

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
        <DevicesTab devices={devices} deviceTableColumns={deviceTableColumns} onRefresh={refreshDevices} />
      )}

      {activeTab === "runner" && (
        <RunnerTab
          selectedDevice={selectedDevice}
          selectedApp={selectedApp}
          selectedPackage={selectedPackage}
          suite={suite}
          deviceSelectOptions={deviceSelectOptions}
          appSelectOptions={appSelectOptions}
          packageSelectOptions={packageSelectOptions}
          suiteOptions={suiteOptions}
          isSelectedDeviceRunning={isSelectedDeviceRunning}
          currentDevice={currentDevice}
          packageLabelMap={packageLabelMap}
          executionPackages={executionPackages}
          selectedExecutionIndex={selectedExecutionIndex}
          summaryCardStyle={summaryCardStyle}
          summaryBodyStyle={summaryBodyStyle}
          summaryValueStyle={summaryValueStyle}
          onSelectDevice={setSelectedDevice}
          onSelectApp={setSelectedApp}
          onSelectPackage={(value) => setSelectedPackage(normalizePackageValue(value))}
          onSelectSuite={setSuite}
          onRefreshSelectedDeviceStatus={() => {
            void refreshSelectedDeviceStatus();
          }}
          onRefreshPackages={() => {
            void refreshPackages();
          }}
          onRunTests={() => {
            void runTests();
          }}
          onStopCurrentTask={() => {
            void stopCurrentTask();
          }}
          onSelectExecutionIndex={setSelectedExecutionIndex}
          onAddSelectedCase={addSelectedCase}
          onAddAllCases={addAllCases}
          onRemoveSelectedCase={removeSelectedCase}
          onMoveSelectedCaseUp={() => moveSelectedCase(-1)}
          onMoveSelectedCaseDown={() => moveSelectedCase(1)}
          onClearExecutionPackages={() => {
            setExecutionPackages([]);
            setSelectedExecutionIndex(-1);
          }}
        />
      )}

      {activeTab === "results" && (
        <ResultsTab
          historyStatusFilter={historyStatusFilter}
          historyStatusOptions={historyStatusOptions}
          displayTaskHistory={displayTaskHistory}
          resultsTableColumns={resultsTableColumns}
          currentTaskId={currentTaskId}
          logText={logText}
          onHistoryStatusChange={setHistoryStatusFilter}
          onRefreshHistory={() => {
            void refreshTaskHistory();
          }}
          onRefreshTaskStatus={() => {
            void refreshCurrentTaskStatus();
          }}
          onOpenReport={() => {
            void openReport();
          }}
          onSelectTask={(record) => {
            setCurrentTaskId(record.task_id);
            if (record.has_report_data) {
              setReportTaskId(record.task_id);
            }
            setActiveTab("results");
          }}
        />
      )}

      {activeTab === "report" && (
        <ReportTab
          reportTaskId={reportTaskId}
          reportTasks={reportTasks}
          reportCaseStatusFilter={reportCaseStatusFilter}
          reportCaseStatusOptions={reportCaseStatusOptions}
          selectedReportTask={selectedReportTask}
          reportSummary={reportSummary}
          reportCases={reportCases}
          reportLoading={reportLoading}
          reportTablePagination={reportTablePagination}
          reportCaseColumns={reportCaseColumns}
          onReportTaskChange={setReportTaskId}
          onReportCaseStatusChange={(value) => {
            setReportCaseStatusFilter(value);
            setReportPage(1);
          }}
          onRefreshReport={() => {
            void refreshTaskReportData();
          }}
          onOpenHtmlReport={() => {
            if (!selectedReportTask?.has_report) return;
            const url =
              selectedReportTask.report_url ||
              "/api/task_report/" + encodeURIComponent(selectedReportTask.task_id);
            window.open(url, "_blank");
          }}
        />
      )}
    </div>
  );
}

export default App;














