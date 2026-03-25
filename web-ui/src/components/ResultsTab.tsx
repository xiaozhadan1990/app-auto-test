import { Button, Card, Select, Space, Table } from "antd";
import type { TableProps } from "antd";
import type { TaskHistoryItem } from "../types/app";

type SelectOption = {
  value: string;
  label: string;
};

type ResultsTabProps = {
  historyStatusFilter: string;
  historyStatusOptions: SelectOption[];
  displayTaskHistory: TaskHistoryItem[];
  resultsTableColumns: TableProps<TaskHistoryItem>["columns"];
  currentTaskId?: string;
  logText: string;
  onHistoryStatusChange: (value: string) => void;
  onRefreshHistory: () => void;
  onRefreshTaskStatus: () => void;
  onOpenReport: () => void;
  onSelectTask: (task: TaskHistoryItem) => void;
};

function ResultsTab({
  historyStatusFilter,
  historyStatusOptions,
  displayTaskHistory,
  resultsTableColumns,
  currentTaskId,
  logText,
  onHistoryStatusChange,
  onRefreshHistory,
  onRefreshTaskStatus,
  onOpenReport,
  onSelectTask,
}: ResultsTabProps) {
  return (
    <Card
      title="执行结果"
      extra={
        <Space>
          <Select
            style={{ width: 150 }}
            value={historyStatusFilter}
            onChange={onHistoryStatusChange}
            options={historyStatusOptions}
          />
          <Button onClick={onRefreshHistory}>刷新历史</Button>
          <Button onClick={onRefreshTaskStatus} disabled={!currentTaskId}>
            刷新任务状态
          </Button>
          <Button onClick={onOpenReport}>打开最近报告</Button>
        </Space>
      }
    >
      <Table
        rowKey="task_id"
        size="small"
        pagination={{ pageSize: 8, hideOnSinglePage: true }}
        dataSource={displayTaskHistory}
        onRow={(record) => ({
          onClick: () => onSelectTask(record),
          style: { cursor: "pointer" },
        })}
        columns={resultsTableColumns}
        style={{ marginBottom: 12 }}
      />
      <pre
        style={{
          margin: 0,
          whiteSpace: "pre-wrap",
          background: "#0f172a",
          color: "#e2e8f0",
          borderRadius: 8,
          padding: 10,
          minHeight: 180,
          maxHeight: 460,
          overflow: "auto",
          fontSize: 12,
        }}
      >
        {logText}
      </pre>
    </Card>
  );
}

export default ResultsTab;
