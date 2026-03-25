import type { ReactNode } from "react";
import type {
  DeviceRuntimeStatus,
  ReportPagination,
  TaskHistoryItem,
  TaskReportCase,
  TaskReportSummary,
} from "../types/app";

const svgModules = import.meta.glob("../../assets/*.svg", {
  eager: true,
  import: "default",
}) as Record<string, string>;

const phoneSvgMap = Object.fromEntries(
  Object.entries(svgModules).map(([path, url]) => {
    const name = path.split("/").pop()?.replace(".svg", "").toLowerCase() || "";
    return [name, url];
  })
);

export function normalizePackageValue(input: unknown): string | undefined {
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

export function normalizePackageQueue(input: unknown[]): string[] {
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

export function fallbackPackageLabel(packageValue: string): string {
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

export function resolvePackageLabel(input: unknown, labelMap: Record<string, string>): string {
  const value = normalizePackageValue(input);
  if (!value) return "鏈煡鐢ㄤ緥";
  return labelMap[value] || fallbackPackageLabel(value);
}

function normalizeKey(value?: string): string {
  return (value || "").toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function getBrandImageUrl(brand?: string): string | null {
  const key = normalizeKey(brand);
  if (!key) return null;
  if (phoneSvgMap[key]) return phoneSvgMap[key];
  return null;
}

export function renderBrand(brand?: string, imageHeight = 36): ReactNode {
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

export function formatDeviceStatus(status?: string): string {
  const s = (status || "").toLowerCase();
  if (s === "device") return "已连接";
  if (s === "offline") return "绂荤嚎";
  if (s === "unauthorized") return "未授权";
  if (s === "recovery") return "鎭㈠妯″紡";
  return status || "-";
}

export function formatRunStatus(status?: string): string {
  const s = (status || "").toLowerCase();
  if (s === "running") return "运行中";
  if (s === "failed") return "澶辫触";
  if (s === "success") return "鎴愬姛";
  if (s === "idle") return "绌洪棽";
  if (s === "stopped") return "已停止";
  return status || "绌洪棽";
}

export function formatExitCode(code?: number | null): string {
  if (code === null || code === undefined) return "-";
  if (code === 0) return "鎴愬姛";
  if (code === 1) return "澶辫触";
  return `澶辫触(閫€鍑虹爜${code})`;
}

export function formatCaseStatus(status?: string): string {
  const s = (status || "").toLowerCase();
  if (s === "passed") return "閫氳繃";
  if (s === "failed") return "澶辫触";
  if (s === "skipped") return "璺宠繃";
  return status || "-";
}

export function hasReportWarning(task: TaskHistoryItem): boolean {
  const status = (task.status || "").toLowerCase();
  if (status !== "success") return false;
  if ((task.allure_exit_code ?? 0) !== 0) return true;
  const output = (task.allure_output || "").toLowerCase();
  return output.includes("failed") || output.includes("warning") || output.includes("warn");
}

export function isSameDeviceRuntimeStatus(
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

export function isSameTaskHistoryList(left: TaskHistoryItem[], right: TaskHistoryItem[]): boolean {
  if (left.length !== right.length) return false;
  for (let i = 0; i < left.length; i += 1) {
    const a = left[i];
    const b = right[i];
    if (
      a.task_id !== b.task_id ||
      a.device_serial !== b.device_serial ||
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

export function isSameReportSummary(left?: TaskReportSummary, right?: TaskReportSummary): boolean {
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

export function isSameReportCases(left: TaskReportCase[], right: TaskReportCase[]): boolean {
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

export function isSameReportPagination(left: ReportPagination, right: ReportPagination): boolean {
  return left.page === right.page && left.page_size === right.page_size && left.total === right.total;
}
