export type Device = {
  serial: string;
  platform?: string;
  status: string;
  brand: string;
  model: string;
  os_version: string;
  app_versions?: Record<string, string>;
  runtime_status?: DeviceRuntimeStatus;
};

export type AppOption = {
  key: string;
  label: string;
};

export type TestPackageOption = {
  value: string;
  label: string;
  tooltip?: string;
  priority?: number;
};

export type ApiOk = {
  ok: boolean;
  error?: string;
};

export type DeviceRuntimeStatus = {
  device_serial: string;
  status: string;
  task_id?: string | null;
  message?: string;
  updated_at?: string | null;
};

export type TaskHistoryItem = {
  task_id: string;
  device_serial: string;
  app_key?: string;
  suite?: string;
  status: string;
  start_time?: string;
  end_time?: string | null;
  run_exit_code?: number | null;
  report_exit_code?: number | null;
  error?: string | null;
  log_path?: string | null;
  report_output?: string | null;
  has_report?: boolean;
  report_url?: string | null;
  has_report_data?: boolean;
};

export type TaskReportSummary = {
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

export type TaskReportCase = {
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
  case_report_path?: string;
  case_report_url?: string | null;
};

export type ReportPagination = {
  page: number;
  page_size: number;
  total: number;
};

export type StartupInfoResponse = {
  ok?: boolean;
  missing_dependencies?: string[];
};

export type DeviceStatusResponse = ApiOk & {
  device_status: DeviceRuntimeStatus;
};

export type TaskHistoryResponse = ApiOk & {
  tasks: TaskHistoryItem[];
};

export type TaskReportDataResponse = ApiOk & {
  task_id: string;
  summary: TaskReportSummary;
  tests: TaskReportCase[];
  pagination: ReportPagination;
};

export type ListDevicesResponse = ApiOk & {
  devices: Device[];
};

export type ListTestPackagesResponse = ApiOk & {
  packages: Array<string | TestPackageOption>;
  package_paths?: string[];
};

export type RunTestsPayload = {
  device: string;
  device_platform?: string;
  app_key: string;
  test_packages: string[];
  suite: string;
};

export type RunTestsResponse = ApiOk & {
  task_id?: string;
  status?: string;
};

export type StopTaskResponse = ApiOk & {
  task_id?: string;
  status?: string;
};

export type StopTaskPayload = {
  task_id?: string;
  device: string;
};

export type TaskStatusResponse = ApiOk & {
  task_id?: string;
  status?: string;
  run_exit_code?: number | null;
  report_exit_code?: number | null;
  log_output?: string;
  report_output?: string;
  error?: string;
  device?: string;
  has_report?: boolean;
  report_url?: string | null;
  has_report_data?: boolean;
};
