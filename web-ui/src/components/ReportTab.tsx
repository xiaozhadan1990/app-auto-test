import { Alert, Button, Card, Col, Row, Select, Space, Table, Typography } from "antd";
import type { TableProps } from "antd";
import type { TaskHistoryItem, TaskReportCase, TaskReportSummary } from "../types/app";

type SelectOption = {
  value: string;
  label: string;
};

type ReportTabProps = {
  reportTaskId?: string;
  reportTasks: SelectOption[];
  reportCaseStatusFilter: string;
  reportCaseStatusOptions: SelectOption[];
  selectedReportTask?: TaskHistoryItem;
  reportSummary?: TaskReportSummary;
  reportCases: TaskReportCase[];
  reportLoading: boolean;
  reportTablePagination: {
    current: number;
    pageSize: number;
    total: number;
    hideOnSinglePage: boolean;
    onChange: (page: number, pageSize: number) => void;
  };
  reportCaseColumns: TableProps<TaskReportCase>["columns"];
  onReportTaskChange: (value: string) => void;
  onReportCaseStatusChange: (value: string) => void;
  onRefreshReport: () => void;
};

function ReportTab({
  reportTaskId,
  reportTasks,
  reportCaseStatusFilter,
  reportCaseStatusOptions,
  selectedReportTask,
  reportSummary,
  reportCases,
  reportLoading,
  reportTablePagination,
  reportCaseColumns,
  onReportTaskChange,
  onReportCaseStatusChange,
  onRefreshReport,
}: ReportTabProps) {
  return (
    <Card
      title="Airtest 报告"
      extra={
        <Space wrap>
          <Select
            style={{ width: 340 }}
            placeholder="选择任务"
            value={reportTaskId}
            onChange={onReportTaskChange}
            options={reportTasks}
          />
          <Select
            style={{ width: 120 }}
            value={reportCaseStatusFilter}
            onChange={onReportCaseStatusChange}
            options={reportCaseStatusOptions}
          />
          <Button onClick={onRefreshReport}>刷新报告</Button>
        </Space>
      }
    >
      {!reportTaskId && (
        <Alert
          type="info"
          showIcon
          message="暂无可用测试报告，请先至少执行一次测试任务。"
          style={{ marginBottom: 12 }}
        />
      )}
      {reportSummary && (
        <Row gutter={10} style={{ marginBottom: 12 }}>
          <Col span={4}>
            <Card size="small" title="总数">
              <Typography.Title level={4} style={{ margin: 0 }}>
                {reportSummary.total}
              </Typography.Title>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" title="通过">
              <Typography.Title level={4} style={{ margin: 0, color: "#16a34a" }}>
                {reportSummary.passed}
              </Typography.Title>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" title="失败">
              <Typography.Title level={4} style={{ margin: 0, color: "#dc2626" }}>
                {reportSummary.failed}
              </Typography.Title>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" title="跳过">
              <Typography.Title level={4} style={{ margin: 0, color: "#d97706" }}>
                {reportSummary.skipped}
              </Typography.Title>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" title="通过率">
              <Typography.Title level={4} style={{ margin: 0 }}>
                {(reportSummary.pass_rate || 0).toFixed(1)}%
              </Typography.Title>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" title="总耗时">
              <Typography.Title level={4} style={{ margin: 0 }}>
                {(reportSummary.total_duration || 0).toFixed(1)}s
              </Typography.Title>
            </Card>
          </Col>
        </Row>
      )}
      <Table
        rowKey={(record) => `${record.task_id}-${record.case_index}`}
        size="small"
        loading={reportLoading}
        pagination={reportTablePagination}
        dataSource={reportCases}
        expandable={{
          expandedRowRender: (record) => (
            <div>
              <div>
                <b>节点：</b> {record.node_id || "-"}
              </div>
              <div style={{ marginTop: 6 }}>
                <b>错误：</b> {record.error_message || "-"}
              </div>
              <Space style={{ marginTop: 8 }}>
                <Button
                  size="small"
                  disabled={!record.case_report_url}
                  onClick={() => record.case_report_url && window.open(record.case_report_url, "_blank")}
                >
                  查看 Airtest 报告
                </Button>
              </Space>
            </div>
          ),
        }}
        columns={reportCaseColumns}
      />
    </Card>
  );
}

export default ReportTab;
