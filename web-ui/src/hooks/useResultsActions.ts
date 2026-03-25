import type { Dispatch, SetStateAction } from "react";
import type { TaskHistoryItem } from "../types/app";

type UseResultsActionsOptions = {
  refreshTaskHistory: () => Promise<void>;
  refreshCurrentTaskStatus: () => Promise<void>;
  openReport: () => Promise<void>;
  setCurrentTaskId: Dispatch<SetStateAction<string | undefined>>;
  setReportTaskId: Dispatch<SetStateAction<string | undefined>>;
};

function useResultsActions({
  refreshTaskHistory,
  refreshCurrentTaskStatus,
  openReport,
  setCurrentTaskId,
  setReportTaskId,
}: UseResultsActionsOptions) {
  const handleRefreshHistory = () => {
    void refreshTaskHistory();
  };

  const handleRefreshTaskStatus = () => {
    void refreshCurrentTaskStatus();
  };

  const handleOpenLatestReport = () => {
    void openReport();
  };

  const handleSelectTask = (record: TaskHistoryItem) => {
    setCurrentTaskId(record.task_id);
    if (record.has_report_data) {
      setReportTaskId(record.task_id);
    }
  };

  return {
    handleRefreshHistory,
    handleRefreshTaskStatus,
    handleOpenLatestReport,
    handleSelectTask,
  };
}

export default useResultsActions;
