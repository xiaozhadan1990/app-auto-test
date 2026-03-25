import { useEffect, useMemo, useState } from "react";
import { isSameReportCases, isSameReportPagination, isSameReportSummary } from "../lib/appHelpers";
import { getTaskReportData } from "../lib/api";
import type { ReportPagination, TaskHistoryItem, TaskReportCase, TaskReportSummary } from "../types/app";

type MessageApi = {
  error: (content: string) => void;
};

type UseReportStateOptions = {
  activeTab: string;
  taskHistory: TaskHistoryItem[];
  msgApi: MessageApi;
};

function useReportState({ activeTab, taskHistory, msgApi }: UseReportStateOptions) {
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

  const reportTasks = useMemo(
    () =>
      taskHistory
        .filter((t) => t.has_report_data)
        .map((t) => ({ value: t.task_id, label: `${t.task_id} | ${t.start_time || "-"}` })),
    [taskHistory]
  );
  const selectedReportTask = useMemo(
    () => taskHistory.find((t) => t.task_id === reportTaskId),
    [taskHistory, reportTaskId]
  );
  const shouldLoadReportData = activeTab === "report" && Boolean(reportTaskId);
  const shouldPollReportData = shouldLoadReportData && selectedReportTask?.status === "running";
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

  const refreshTaskReportData = async (taskId?: string) => {
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

  useEffect(() => {
    setReportTaskId((old) => {
      if (old && taskHistory.some((t) => t.task_id === old && t.has_report_data)) return old;
      return taskHistory.find((t) => t.has_report_data)?.task_id;
    });
  }, [taskHistory]);

  useEffect(() => {
    setReportPage(1);
  }, [reportTaskId, reportCaseStatusFilter]);

  useEffect(() => {
    if (!shouldLoadReportData || !reportTaskId) return;
    void refreshTaskReportData(reportTaskId);
  }, [reportCaseStatusFilter, reportPage, reportPageSize, reportTaskId, shouldLoadReportData]);

  useEffect(() => {
    if (!shouldPollReportData || !reportTaskId) return;
    const timer = window.setInterval(() => {
      void refreshTaskReportData(reportTaskId);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [reportTaskId, shouldPollReportData, reportCaseStatusFilter, reportPage, reportPageSize]);

  return {
    reportTaskId,
    reportSummary,
    reportCases,
    reportLoading,
    reportCaseStatusFilter,
    reportPage,
    reportPageSize,
    reportPagination,
    reportTasks,
    selectedReportTask,
    reportTablePagination,
    setReportTaskId,
    setReportCaseStatusFilter,
    setReportPage,
    setReportPageSize,
    refreshTaskReportData,
  };
}

export default useReportState;
