import { Suspense, lazy, useState } from "react";
import { Card, Spin, message, Tabs, Typography } from "antd";
import StartupAlert from "./components/StartupAlert";
import useExecutionQueue from "./hooks/useExecutionQueue";
import useReportActions from "./hooks/useReportActions";
import useReportState from "./hooks/useReportState";
import useResultsActions from "./hooks/useResultsActions";
import useRunnerSetup from "./hooks/useRunnerSetup";
import useTaskActions from "./hooks/useTaskActions";
import useTaskMonitor from "./hooks/useTaskMonitor";
import {
  getDeviceSelectOptions,
  getDeviceTableColumns,
  getHistoryStatusOptions,
  getReportCaseColumns,
  getReportCaseStatusOptions,
  getResultsTableColumns,
  getSuiteOptions,
  getSummaryStyles,
  getTabItems,
} from "./lib/appViewConfig";

const DevicesTab = lazy(() => import("./components/DevicesTab"));
const ReportTab = lazy(() => import("./components/ReportTab"));
const ResultsTab = lazy(() => import("./components/ResultsTab"));
const RunnerTab = lazy(() => import("./components/RunnerTab"));

function App() {
  const [msgApi, contextHolder] = message.useMessage();
  const [activeTab, setActiveTab] = useState("devices");
  const [logText, setLogText] = useState("等待执行...");
  const { summaryCardStyle, summaryBodyStyle, summaryValueStyle } = getSummaryStyles();

  const runnerState = useRunnerSetup({ setLogText });
  const queueState = useExecutionQueue({
    packages: runnerState.packages,
    selectedPackage: runnerState.selectedPackage,
    msgApi,
  });
  const taskMonitor = useTaskMonitor({
    activeTab,
    selectedDevice: runnerState.selectedDevice,
    startupReady: runnerState.startupReady,
    refreshDeviceRuntime: runnerState.refreshDeviceRuntime,
    msgApi,
    setLogText,
  });
  const reportState = useReportState({
    activeTab,
    taskHistory: taskMonitor.taskHistory,
    msgApi,
  });
  const taskActions = useTaskActions({
    msgApi,
    setActiveTab,
    setLogText,
    selectedDevice: runnerState.selectedDevice,
    selectedApp: runnerState.selectedApp,
    isSelectedDeviceRunning: runnerState.isSelectedDeviceRunning,
    executionPackages: queueState.executionPackages,
    suite: queueState.suite,
    currentTaskId: taskMonitor.currentTaskId,
    setCurrentTaskId: taskMonitor.setCurrentTaskId,
    refreshDeviceRuntime: runnerState.refreshDeviceRuntime,
    refreshTaskHistory: taskMonitor.refreshTaskHistory,
  });
  const resultsActions = useResultsActions({
    refreshTaskHistory: taskMonitor.refreshTaskHistory,
    refreshCurrentTaskStatus: taskMonitor.refreshCurrentTaskStatus,
    openReport: taskActions.openReport,
    setCurrentTaskId: taskMonitor.setCurrentTaskId,
    setReportTaskId: reportState.setReportTaskId,
  });
  const reportActions = useReportActions({
    selectedReportTask: reportState.selectedReportTask,
    setReportCaseStatusFilter: reportState.setReportCaseStatusFilter,
    setReportPage: reportState.setReportPage,
    refreshTaskReportData: reportState.refreshTaskReportData,
  });

  const suiteOptions = getSuiteOptions();
  const historyStatusOptions = getHistoryStatusOptions();
  const reportCaseStatusOptions = getReportCaseStatusOptions();
  const tabItems = getTabItems();
  const deviceTableColumns = getDeviceTableColumns(runnerState.deviceRuntimeMap);
  const resultsTableColumns = getResultsTableColumns();
  const reportCaseColumns = getReportCaseColumns();
  const deviceSelectOptions = getDeviceSelectOptions(runnerState.devices);

  return (
    <div style={{ width: "calc(100% - 24px)", maxWidth: "none", margin: "8px 12px 16px", padding: 0 }}>
      {contextHolder}
      <Typography.Title level={3} style={{ marginTop: 4 }}>
        移动自动化测试桌面端
      </Typography.Title>

      <StartupAlert startupMissing={runnerState.startupMissing} />

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>

      <Suspense
        fallback={
          <Card style={{ marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "center", padding: "32px 0" }}>
              <Spin tip="页面加载中..." />
            </div>
          </Card>
        }
      >
        {activeTab === "devices" && (
          <DevicesTab
            devices={runnerState.devices}
            deviceTableColumns={deviceTableColumns}
            onRefresh={runnerState.refreshDevices}
          />
        )}

        {activeTab === "runner" && (
          <RunnerTab
            selectedDevice={runnerState.selectedDevice}
            selectedApp={runnerState.selectedApp}
            selectedPackage={runnerState.selectedPackage}
            suite={queueState.suite}
            deviceSelectOptions={deviceSelectOptions}
            appSelectOptions={runnerState.appSelectOptions}
            packageSelectOptions={runnerState.packageSelectOptions}
            suiteOptions={suiteOptions}
            isSelectedDeviceRunning={runnerState.isSelectedDeviceRunning}
            currentDevice={runnerState.currentDevice}
            packageLabelMap={runnerState.packageLabelMap}
            executionPackages={queueState.executionPackages}
            selectedExecutionIndex={queueState.selectedExecutionIndex}
            summaryCardStyle={summaryCardStyle}
            summaryBodyStyle={summaryBodyStyle}
            summaryValueStyle={summaryValueStyle}
            onSelectDevice={runnerState.setSelectedDevice}
            onSelectApp={runnerState.setSelectedApp}
            onSelectPackage={runnerState.setSelectedPackage}
            onSelectSuite={queueState.setSuite}
            onRefreshSelectedDeviceStatus={() => {
              void taskMonitor.refreshSelectedDeviceStatus();
            }}
            onRefreshPackages={() => {
              void runnerState.refreshPackages();
            }}
            onRunTests={() => {
              void taskActions.runTests();
            }}
            onStopCurrentTask={() => {
              void taskActions.stopCurrentTask();
            }}
            onSelectExecutionIndex={queueState.setSelectedExecutionIndex}
            onAddSelectedCase={queueState.addSelectedCase}
            onAddAllCases={queueState.addAllCases}
            onRemoveSelectedCase={queueState.removeSelectedCase}
            onMoveSelectedCaseUp={() => queueState.moveSelectedCase(-1)}
            onMoveSelectedCaseDown={() => queueState.moveSelectedCase(1)}
            onClearExecutionPackages={queueState.clearExecutionPackages}
          />
        )}

        {activeTab === "results" && (
          <ResultsTab
            historyStatusFilter={taskMonitor.historyStatusFilter}
            historyStatusOptions={historyStatusOptions}
            displayTaskHistory={taskMonitor.displayTaskHistory}
            resultsTableColumns={resultsTableColumns}
            currentTaskId={taskMonitor.currentTaskId}
            logText={logText}
            onHistoryStatusChange={taskMonitor.setHistoryStatusFilter}
            onRefreshHistory={resultsActions.handleRefreshHistory}
            onRefreshTaskStatus={resultsActions.handleRefreshTaskStatus}
            onOpenReport={resultsActions.handleOpenLatestReport}
            onSelectTask={resultsActions.handleSelectTask}
          />
        )}

        {activeTab === "report" && (
          <ReportTab
            reportTaskId={reportState.reportTaskId}
            reportTasks={reportState.reportTasks}
            reportCaseStatusFilter={reportState.reportCaseStatusFilter}
            reportCaseStatusOptions={reportCaseStatusOptions}
            selectedReportTask={reportState.selectedReportTask}
            reportSummary={reportState.reportSummary}
            reportCases={reportState.reportCases}
            reportLoading={reportState.reportLoading}
            reportTablePagination={reportState.reportTablePagination}
            reportCaseColumns={reportCaseColumns}
            onReportTaskChange={reportState.setReportTaskId}
            onReportCaseStatusChange={reportActions.handleReportCaseStatusChange}
            onRefreshReport={reportActions.handleRefreshReport}
            onOpenHtmlReport={reportActions.handleOpenHtmlReport}
          />
        )}
      </Suspense>
    </div>
  );
}

export default App;
