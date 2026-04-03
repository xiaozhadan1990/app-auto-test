import type { Dispatch, SetStateAction } from "react";
import type { TaskHistoryItem } from "../types/app";

type UseResultsActionsOptions = {
  refreshTaskHistory: () => Promise<void>;
  refreshCurrentTaskStatus: () => Promise<void>;
  setActiveTab: Dispatch<SetStateAction<string>>;
  setCurrentTaskId: Dispatch<SetStateAction<string | undefined>>;
  setReportTaskId: Dispatch<SetStateAction<string | undefined>>;
};

function useResultsActions({
  refreshTaskHistory,
  refreshCurrentTaskStatus,
  setActiveTab,
  setCurrentTaskId,
  setReportTaskId,
}: UseResultsActionsOptions) {
  const handleRefreshHistory = () => {
    void refreshTaskHistory();
  };

  const handleRefreshTaskStatus = () => {
    void refreshCurrentTaskStatus();
  };

  const handleSelectTask = (record: TaskHistoryItem) => {
    setCurrentTaskId(record.task_id);
    if (record.has_report_data) {
      setReportTaskId(record.task_id);
    }
  };

  const handleViewTaskReport = (record: TaskHistoryItem) => {
    setCurrentTaskId(record.task_id);
    if (!record.has_report_data) return;
    setReportTaskId(record.task_id);
    setActiveTab("report");
  };

  return {
    handleRefreshHistory,
    handleRefreshTaskStatus,
    handleSelectTask,
    handleViewTaskReport,
  };
}

export default useResultsActions;
