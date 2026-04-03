import type {
  AppOption,
  AppiumReadyResponse,
  DeviceStatusResponse,
  ListDevicesResponse,
  ListTestPackagesResponse,
  RunTestsPayload,
  RunTestsResponse,
  StartupInfoResponse,
  StopTaskResponse,
  StopTaskPayload,
  TaskHistoryResponse,
  TaskReportDataResponse,
  TaskStatusResponse,
} from "../types/app";

async function apiRequest<T>(path: string, body?: unknown): Promise<T> {
  const resp = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!resp.ok) {
    let errorMessage = `HTTP ${resp.status}`;
    try {
      const payload = (await resp.json()) as { error?: unknown; message?: unknown };
      if (typeof payload.error === "string" && payload.error.trim()) {
        errorMessage = payload.error.trim();
      } else if (typeof payload.message === "string" && payload.message.trim()) {
        errorMessage = payload.message.trim();
      }
    } catch {
      // Fall back to the HTTP status message if the response is not JSON.
    }
    throw new Error(errorMessage);
  }
  return (await resp.json()) as T;
}

export async function getStartupInfo(): Promise<StartupInfoResponse> {
  return apiRequest<StartupInfoResponse>("/api/startup_info");
}

export async function getAppiumReady(): Promise<AppiumReadyResponse> {
  return apiRequest<AppiumReadyResponse>("/api/appium_ready");
}

export async function getDeviceRuntime(deviceSerial: string): Promise<DeviceStatusResponse> {
  return apiRequest<DeviceStatusResponse>(`/api/device_status/${encodeURIComponent(deviceSerial)}`);
}

export async function getTaskHistory(params: {
  device?: string;
  status?: string;
  limit?: number;
}): Promise<TaskHistoryResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("limit", String(params.limit ?? 30));
  if (params.device) searchParams.set("device", params.device);
  if (params.status) searchParams.set("status", params.status);
  return apiRequest<TaskHistoryResponse>(`/api/task_history?${searchParams.toString()}`);
}

export async function getTaskReportData(params: {
  taskId: string;
  page: number;
  pageSize: number;
  status?: string;
}): Promise<TaskReportDataResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("page", String(params.page));
  searchParams.set("page_size", String(params.pageSize));
  if (params.status) {
    searchParams.set("status", params.status);
  }
  return apiRequest<TaskReportDataResponse>(
    `/api/task_report_data/${encodeURIComponent(params.taskId)}?${searchParams.toString()}`
  );
}

export async function listDevices(): Promise<ListDevicesResponse> {
  return apiRequest<ListDevicesResponse>("/api/list_devices", {});
}

export async function getAppOptions(): Promise<AppOption[]> {
  return apiRequest<AppOption[]>("/api/get_app_options");
}

export function listTestPackages(appKey: string, devicePlatform?: string): Promise<ListTestPackagesResponse>;
export function listTestPackages(params: {
  appKey: string;
  devicePlatform?: string;
}): Promise<ListTestPackagesResponse>;
export async function listTestPackages(
  appKeyOrParams: string | { appKey: string; devicePlatform?: string },
  devicePlatformArg?: string
): Promise<ListTestPackagesResponse> {
  const appKey = typeof appKeyOrParams === "string" ? appKeyOrParams : appKeyOrParams.appKey;
  const devicePlatform =
    typeof appKeyOrParams === "string" ? devicePlatformArg : appKeyOrParams.devicePlatform;
  return apiRequest<ListTestPackagesResponse>("/api/list_test_packages", {
    app_key: appKey,
    device_platform: devicePlatform,
  });
}

export async function runTests(payload: RunTestsPayload): Promise<RunTestsResponse> {
  return apiRequest<RunTestsResponse>("/api/run_tests", payload);
}

export async function stopTask(payload: StopTaskPayload): Promise<StopTaskResponse> {
  return apiRequest<StopTaskResponse>("/api/stop_task", payload);
}

export async function openReport(): Promise<{ ok: boolean; error?: string }> {
  return apiRequest<{ ok: boolean; error?: string }>("/api/open_report", {});
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  return apiRequest<TaskStatusResponse>(`/api/task_status/${encodeURIComponent(taskId)}`);
}
