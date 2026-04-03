import { useEffect, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import {
  fallbackPackageLabel,
  formatPackageLabel,
  isSameDeviceRuntimeStatus,
  normalizePackageValue,
} from "../lib/appHelpers";
import { getAppOptions, getDeviceRuntime, getStartupInfo, listDevices, listTestPackages } from "../lib/api";
import type { AppOption, Device, DeviceRuntimeStatus, TestPackageOption } from "../types/app";

type UseRunnerSetupOptions = {
  setLogText: Dispatch<SetStateAction<string>>;
};

function isAllCasesValue(value: string): boolean {
  return !value.endsWith(".py");
}

function useRunnerSetup({ setLogText }: UseRunnerSetupOptions) {
  const [startupMissing, setStartupMissing] = useState<string[]>([]);
  const [startupReady, setStartupReady] = useState(false);
  const [devices, setDevices] = useState<Device[]>([]);
  const [apps, setApps] = useState<AppOption[]>([]);
  const [packages, setPackages] = useState<TestPackageOption[]>([]);
  const [deviceRuntimeMap, setDeviceRuntimeMap] = useState<Record<string, DeviceRuntimeStatus>>({});
  const [selectedDevice, setSelectedDevice] = useState<string>();
  const [selectedApp, setSelectedApp] = useState<string>();
  const [selectedPackage, setSelectedPackage] = useState<string>();

  const currentDevice = useMemo(
    () => devices.find((d) => d.serial === selectedDevice),
    [devices, selectedDevice]
  );
  const selectedDeviceRuntime = selectedDevice ? deviceRuntimeMap[selectedDevice] : undefined;
  const isSelectedDeviceRunning = selectedDeviceRuntime?.status === "running";

  const deviceSelectOptions = useMemo(
    () => devices.map((d) => ({ value: d.serial, label: `${d.serial} (${d.status})` })),
    [devices]
  );
  const appSelectOptions = useMemo(
    () => apps.map((a) => ({ value: a.key, label: a.label })),
    [apps]
  );
  const packageSelectOptions = useMemo(
    () =>
      [...packages]
        .sort((left, right) => {
          const leftIsAll = left.priority === 0 && isAllCasesValue(left.value);
          const rightIsAll = right.priority === 0 && isAllCasesValue(right.value);
          if (leftIsAll !== rightIsAll) {
            return leftIsAll ? -1 : 1;
          }
          return 0;
        })
        .map((item) => {
          const isAllCases = item.priority === 0 && isAllCasesValue(item.value);
          const displayLabel = isAllCases
            ? `${item.label}（按 case_priority 执行）`
            : formatPackageLabel(item.label, item.priority);
          return {
            value: item.value,
            label: displayLabel,
            title: item.tooltip || displayLabel,
          };
        }),
    [packages]
  );
  const packageLabelMap = useMemo(() => {
    const map: Record<string, string> = {};
    for (const item of packages) {
      const value = normalizePackageValue(item.value);
      if (!value) continue;
      const label = (item.label || "").trim() || fallbackPackageLabel(value);
      map[value] = isAllCasesValue(value) ? label : formatPackageLabel(label, item.priority);
    }
    return map;
  }, [packages]);

  const refreshDeviceRuntime = async (deviceSerial: string) => {
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

  const refreshDevices = async () => {
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
      setSelectedDevice((old) => (old && list.some((d) => d.serial === old) ? old : list[0].serial));
    } else {
      setSelectedDevice(undefined);
      setDeviceRuntimeMap({});
      setLogText("未找到可用设备，请检查 adb devices。");
    }
  };

  const refreshApps = async () => {
    const res = await getAppOptions();
    setApps(res || []);
    if (res?.length) {
      setSelectedApp((old) => (old && res.some((a) => a.key === old) ? old : res[0].key));
    }
  };

  const refreshPackages = async (appKey?: string) => {
    const targetApp = appKey || selectedApp;
    if (!targetApp) return;
    const res = await listTestPackages({
      appKey: targetApp,
      devicePlatform: currentDevice?.platform,
    });
    if (!res.ok) {
      setLogText(`加载用例列表失败\n${res.error || "unknown error"}`);
      return;
    }
    const rawList = Array.isArray(res.packages) ? res.packages : [];
    const list: TestPackageOption[] = rawList
      .map<TestPackageOption | null>((entry) => {
        if (typeof entry === "string") {
          return { value: entry, label: entry };
        }
        const value = String(entry?.value || "").trim();
        if (!value) return null;
        const label = String(entry?.label || value).trim() || value;
        const tooltip = String(entry?.tooltip || "").trim();
        const priorityRaw = (entry as { priority?: unknown }).priority;
        const priority = typeof priorityRaw === "number" && Number.isFinite(priorityRaw) ? priorityRaw : undefined;
        return { value, label, tooltip: tooltip || label, priority };
      })
      .filter((item): item is TestPackageOption => Boolean(item));
    setPackages(list);
    const values = list.map((item) => item.value);
    setSelectedPackage((old) => {
      const normalized = normalizePackageValue(old);
      return normalized && values.includes(normalized) ? normalized : values[0];
    });
    setLogText("用例列表已刷新。");
  };

  useEffect(() => {
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
    if (selectedApp) {
      void refreshPackages(selectedApp);
    }
  }, [selectedApp, selectedDevice]);

  return {
    startupMissing,
    startupReady,
    devices,
    apps,
    packages,
    selectedDevice,
    selectedApp,
    selectedPackage,
    deviceRuntimeMap,
    currentDevice,
    isSelectedDeviceRunning,
    packageLabelMap,
    deviceSelectOptions,
    appSelectOptions,
    packageSelectOptions,
    setSelectedDevice,
    setSelectedApp,
    setSelectedPackage,
    refreshDeviceRuntime,
    refreshDevices,
    refreshApps,
    refreshPackages,
  };
}

export default useRunnerSetup;
