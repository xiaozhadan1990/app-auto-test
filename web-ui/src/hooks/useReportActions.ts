import type { Dispatch, SetStateAction } from "react";
import type { TaskHistoryItem } from "../types/app";

type UseReportActionsOptions = {
  selectedReportTask?: TaskHistoryItem;
  setReportCaseStatusFilter: Dispatch<SetStateAction<string>>;
  setReportPage: Dispatch<SetStateAction<number>>;
  refreshTaskReportData: () => Promise<void>;
};

function useReportActions({
  selectedReportTask,
  setReportCaseStatusFilter,
  setReportPage,
  refreshTaskReportData,
}: UseReportActionsOptions) {
  const handleReportCaseStatusChange = (value: string) => {
    setReportCaseStatusFilter(value);
    setReportPage(1);
  };

  const handleRefreshReport = () => {
    void refreshTaskReportData();
  };

  const handleOpenHtmlReport = () => {
    if (!selectedReportTask?.has_report) return;
    const url =
      selectedReportTask.report_url ||
      `/api/task_report/${encodeURIComponent(selectedReportTask.task_id)}`;
    window.open(url, "_blank");
  };

  return {
    handleReportCaseStatusChange,
    handleRefreshReport,
    handleOpenHtmlReport,
  };
}

export default useReportActions;
