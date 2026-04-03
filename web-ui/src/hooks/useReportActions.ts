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

  return {
    handleReportCaseStatusChange,
    handleRefreshReport,
  };
}

export default useReportActions;
