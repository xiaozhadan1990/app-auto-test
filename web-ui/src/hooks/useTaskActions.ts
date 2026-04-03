import type { Dispatch, SetStateAction } from "react";
import { getAppiumReady, openReport as openReportRequest, runTests as runTestsRequest, stopTask } from "../lib/api";

type MessageApi = {
  error: (content: string) => void;
  warning: (content: string) => void;
  info: (content: string) => void;
  success: (content: string) => void;
};

type UseTaskActionsOptions = {
  msgApi: MessageApi;
  setActiveTab: Dispatch<SetStateAction<string>>;
  setLogText: Dispatch<SetStateAction<string>>;
  selectedDevice?: string;
  selectedDevicePlatform?: string;
  selectedApp?: string;
  isSelectedDeviceRunning: boolean;
  executionPackages: string[];
  suite: string;
  currentTaskId?: string;
  setCurrentTaskId: (taskId?: string) => void;
  refreshDeviceRuntime: (deviceSerial: string) => Promise<unknown>;
  refreshTaskHistory: () => Promise<void>;
};

function useTaskActions({
  msgApi,
  setActiveTab,
  setLogText,
  selectedDevice,
  selectedDevicePlatform,
  selectedApp,
  isSelectedDeviceRunning,
  executionPackages,
  suite,
  currentTaskId,
  setCurrentTaskId,
  refreshDeviceRuntime,
  refreshTaskHistory,
}: UseTaskActionsOptions) {
  const runTests = async () => {
    try {
      const appium = await getAppiumReady();
      if (!appium.running) {
        const addr = appium.server_url || "http://127.0.0.1:4723";
        msgApi.error(`Appium 未启动（${addr}）`);
        setLogText(
          `执行已取消：Appium 未启动\n地址：${addr}\n详情：${appium.error || "unknown error"}`
        );
        setActiveTab("results");
        return;
      }

      if (!executionPackages.length) {
        msgApi.error("请先添加至少一个待执行用例");
        return;
      }
      if (!selectedDevice) {
        msgApi.error("请先选择测试设备");
        return;
      }
      if (!selectedApp) {
        msgApi.error("请先选择应用");
        return;
      }
      if (isSelectedDeviceRunning) {
        msgApi.warning("该设备已有任务在运行中，不能重复启动");
        return;
      }

      setActiveTab("results");
      setLogText(
        `正在执行测试，请稍候...\n执行顺序：\n${executionPackages
          .map((pkg, index) => `${index + 1}. ${pkg}`)
          .join("\n")}`
      );

      const res = await runTestsRequest({
        device: selectedDevice,
        device_platform: selectedDevicePlatform,
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
        msgApi.success(`任务已启动：${res.task_id}`);
        setLogText((old) => `${old}\n\n任务已创建：${res.task_id}`);
      }
    } catch (err) {
      msgApi.error("启动任务失败");
      setLogText(`执行失败\n\n${String(err)}`);
    }
  };

  const stopCurrentTask = async () => {
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
    const res = await openReportRequest();
    if (!res.ok) {
      msgApi.error(res.error || "打开报告失败");
    }
  };

  return {
    runTests,
    stopCurrentTask,
    openReport,
  };
}

export default useTaskActions;
