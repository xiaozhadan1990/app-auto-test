import { LoadingOutlined } from "@ant-design/icons";
import { Button, Space, Tag } from "antd";
import type { CSSProperties, ReactNode } from "react";
import {
  formatCaseStatus,
  formatDeviceStatus,
  formatExitCode,
  formatRunStatus,
  hasReportWarning,
  renderBrand,
} from "./appHelpers";
import type { Device, TaskHistoryItem, TaskReportCase } from "../types/app";

export type SelectOption = {
  value: string;
  label: string;
  title?: string;
};

export function getSummaryStyles(): {
  summaryCardStyle: CSSProperties;
  summaryBodyStyle: CSSProperties;
  summaryValueStyle: CSSProperties;
} {
  return {
    summaryCardStyle: { height: 132 },
    summaryBodyStyle: {
      minHeight: 86,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    },
    summaryValueStyle: { fontSize: 26, fontWeight: 700, lineHeight: 1.1 },
  };
}

export function getTabItems() {
  return [
    { key: "devices", label: "手机终端" },
    { key: "runner", label: "用例执行" },
    { key: "results", label: "执行结果" },
    { key: "report", label: "测试报告" },
  ];
}

export function getSuiteOptions(): SelectOption[] {
  return [
    { value: "all", label: "全部" },
    { value: "smoke", label: "冒烟测试" },
    { value: "full", label: "全量测试" },
  ];
}

export function getHistoryStatusOptions(): SelectOption[] {
  return [
    { value: "all", label: "全部状态" },
    { value: "running", label: "运行中" },
    { value: "success", label: "成功" },
    { value: "failed", label: "失败" },
    { value: "stopped", label: "已停止" },
    { value: "report_warning", label: "仅报告告警" },
  ];
}

export function getReportCaseStatusOptions(): SelectOption[] {
  return [
    { value: "all", label: "全部状态" },
    { value: "passed", label: "通过" },
    { value: "failed", label: "失败" },
    { value: "skipped", label: "跳过" },
  ];
}

export function getDeviceSelectOptions(devices: Device[]): SelectOption[] {
  return devices.map((device) => ({
    value: device.serial,
    label: `${device.serial} (${formatDeviceStatus(device.status)})`,
  }));
}

export function getDeviceTableColumns(
  deviceRuntimeMap: Record<string, { status?: string }>
): Array<Record<string, unknown>> {
  return [
    { title: "设备序列号", dataIndex: "serial" },
    { title: "平台", render: (_: unknown, device: Device) => (device.platform || "android").toUpperCase() },
    { title: "设备状态", render: (_: unknown, device: Device) => formatDeviceStatus(device.status) },
    {
      title: "任务状态",
      render: (_: unknown, device: Device): ReactNode => {
        const status = (deviceRuntimeMap[device.serial]?.status || "").toLowerCase();
        const color =
          status === "success"
            ? "green"
            : status === "failed"
              ? "red"
              : status === "running"
                ? "blue"
                : status === "stopped"
                  ? "orange"
                  : "default";
        return (
          <Tag color={color} icon={status === "running" ? <LoadingOutlined spin /> : undefined}>
            {formatRunStatus(status)}
          </Tag>
        );
      },
    },
    { title: "品牌", render: (_: unknown, device: Device) => renderBrand(device.brand, 32) },
    { title: "型号", dataIndex: "model" },
    { title: "系统版本", dataIndex: "os_version" },
    {
      title: "应用版本",
      render: (_: unknown, device: Device) =>
        `Lysora: ${(device.app_versions && device.app_versions.lysora) || "-"} / RuijieCloud: ${
          (device.app_versions && device.app_versions.ruijieCloud) || "-"
        } / Reyee: ${(device.app_versions && device.app_versions.reyee) || "-"}`,
    },
  ];
}

export function getResultsTableColumns(): Array<Record<string, unknown>> {
  return [
    { title: "任务 ID", dataIndex: "task_id", width: 130 },
    { title: "设备", dataIndex: "device_serial", width: 140 },
    {
      title: "状态",
      width: 190,
      render: (_: unknown, record: TaskHistoryItem): ReactNode => {
        const status = (record.status || "").toLowerCase();
        const color =
          status === "success"
            ? "green"
            : status === "failed"
              ? "red"
              : status === "running"
                ? "blue"
                : status === "stopped"
                  ? "orange"
                  : "default";
        const warn = hasReportWarning(record);
        return (
          <Space size={6}>
            <Tag color={color} icon={status === "running" ? <LoadingOutlined spin /> : undefined}>
              {formatRunStatus(record.status)}
            </Tag>
            {warn && (
              <Tag color="gold" title={record.allure_output || "报告后处理存在告警"}>
                报告告警
              </Tag>
            )}
          </Space>
        );
      },
    },
    { title: "开始时间", dataIndex: "start_time", width: 170 },
    { title: "结束时间", dataIndex: "end_time", width: 170 },
    {
      title: "Pytest 结果",
      render: (_: unknown, record: TaskHistoryItem) => formatExitCode(record.pytest_exit_code),
      width: 120,
    },
    {
      title: "报告结果",
      render: (_: unknown, record: TaskHistoryItem) => formatExitCode(record.allure_exit_code),
      width: 120,
    },
    {
      title: "操作",
      width: 180,
      render: (_: unknown, record: TaskHistoryItem): ReactNode => (
        <Space size={6}>
          <Button
            size="small"
            disabled={!record.has_report}
            onClick={(event) => {
              event.stopPropagation();
              if (!record.has_report) return;
              const url = record.report_url || `/api/task_report/${encodeURIComponent(record.task_id)}`;
              window.open(url, "_blank");
            }}
          >
            查看报告
          </Button>
          <Button
            size="small"
            onClick={(event) => {
              event.stopPropagation();
              window.open(`/api/task_log/${encodeURIComponent(record.task_id)}`, "_blank");
            }}
          >
            下载日志
          </Button>
        </Space>
      ),
    },
  ];
}

export function getReportCaseColumns(): Array<Record<string, unknown>> {
  return [
    { title: "#", dataIndex: "case_index", width: 50 },
    { title: "测试用例", dataIndex: "name", ellipsis: true },
    {
      title: "状态",
      width: 90,
      render: (_: unknown, record: TaskReportCase): ReactNode => {
        const status = (record.status || "").toLowerCase();
        const color =
          status === "passed"
            ? "green"
            : status === "failed"
              ? "red"
              : status === "skipped"
                ? "orange"
                : "default";
        return <Tag color={color}>{formatCaseStatus(record.status)}</Tag>;
      },
    },
    {
      title: "耗时",
      width: 90,
      render: (_: unknown, record: TaskReportCase) => `${(record.duration || 0).toFixed(2)}s`,
    },
    { title: "应用", dataIndex: "app", width: 100 },
  ];
}
