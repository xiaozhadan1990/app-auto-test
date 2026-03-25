import { useEffect, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { formatExitCode, formatRunStatus, hasReportWarning, isSameTaskHistoryList } from "../lib/appHelpers";
import { getTaskHistory, getTaskStatus } from "../lib/api";
import type { DeviceRuntimeStatus, TaskHistoryItem } from "../types/app";

type MessageApi = {
  error: (content: string) => void;
  warning: (content: string) => void;
  info: (content: string) => void;
};

type UseTaskMonitorOptions = {
  activeTab: string;
  selectedDevice?: string;
  startupReady: boolean;
  refreshDeviceRuntime: (deviceSerial: string) => Promise<DeviceRuntimeStatus | null>;
  msgApi: MessageApi;
  setLogText: Dispatch<SetStateAction<string>>;
  onTaskHistoryChange?: (tasks: TaskHistoryItem[]) => void;
};

function useTaskMonitor({
  activeTab,
  selectedDevice,
  startupReady,
  refreshDeviceRuntime,
  msgApi,
  setLogText,
  onTaskHistoryChange,
}: UseTaskMonitorOptions) {
  const [currentTaskId, setCurrentTaskId] = useState<string>();
  const [taskHistory, setTaskHistory] = useState<TaskHistoryItem[]>([]);
  const [historyStatusFilter, setHistoryStatusFilter] = useState<string>("all");

  const displayTaskHistory = useMemo(() => {
    if (historyStatusFilter !== "report_warning") return taskHistory;
    return taskHistory.filter((t) => hasReportWarning(t));
  }, [taskHistory, historyStatusFilter]);

  const shouldPollTaskStatus = activeTab === "results" && Boolean(currentTaskId);
  const shouldPollTaskHistory = shouldPollTaskStatus;

  const refreshTaskHistory = async () => {
    const res = await getTaskHistory({
      limit: 30,
      device: selectedDevice,
      status:
        historyStatusFilter !== "all" && historyStatusFilter !== "report_warning"
          ? historyStatusFilter
          : undefined,
    });
    if (res.ok) {
      const list = res.tasks || [];
      setTaskHistory((old) => (isSameTaskHistoryList(old, list) ? old : list));
      onTaskHistoryChange?.(list);
    }
  };

  const refreshSelectedDeviceStatus = async () => {
    if (!selectedDevice) {
      msgApi.warning("请先选择测试设备");
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
    if (!currentTaskId) {
      if (silent) return;
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
      if (!silent) {
        msgApi.error("刷新任务状态失败");
      }
    }
  };

  useEffect(() => {
    if (!startupReady) return;
    void refreshTaskHistory();
  }, [historyStatusFilter, selectedDevice, startupReady]);

  useEffect(() => {
    if (!selectedDevice) return;
    void refreshDeviceRuntime(selectedDevice).then((s) => {
      if (s?.status === "running" && s.task_id) {
        setCurrentTaskId(s.task_id);
      }
    });
  }, [selectedDevice]);

  useEffect(() => {
    if (!shouldPollTaskStatus) return;
    void refreshCurrentTaskStatus({ silent: true });
    const timer = window.setInterval(() => {
      void refreshCurrentTaskStatus({ silent: true });
    }, 3000);
    return () => window.clearInterval(timer);
  }, [currentTaskId, shouldPollTaskStatus]);

  useEffect(() => {
    if (!shouldPollTaskHistory) return;
    const timer = window.setInterval(() => {
      void refreshTaskHistory();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [historyStatusFilter, shouldPollTaskHistory]);

  return {
    currentTaskId,
    taskHistory,
    historyStatusFilter,
    displayTaskHistory,
    shouldPollTaskStatus,
    setCurrentTaskId,
    setHistoryStatusFilter,
    refreshTaskHistory,
    refreshSelectedDeviceStatus,
    refreshCurrentTaskStatus,
  };
}

export default useTaskMonitor;
