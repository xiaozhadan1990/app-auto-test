import { Button, Card, Col, Row, Select, Space } from "antd";
import type { CSSProperties } from "react";
import type { Device } from "../types/app";
import DeviceSummaryCards from "./DeviceSummaryCards";
import TaskQueueCard from "./TaskQueueCard";

type SelectOption = {
  value: string;
  label: string;
  title?: string;
};

type RunnerTabProps = {
  selectedDevice?: string;
  selectedApp?: string;
  selectedPackage?: string;
  suite: string;
  deviceSelectOptions: SelectOption[];
  appSelectOptions: SelectOption[];
  packageSelectOptions: SelectOption[];
  suiteOptions: SelectOption[];
  isSelectedDeviceRunning: boolean;
  currentDevice?: Device;
  packageLabelMap: Record<string, string>;
  executionPackages: string[];
  selectedExecutionIndex: number;
  summaryCardStyle: CSSProperties;
  summaryBodyStyle: CSSProperties;
  summaryValueStyle: CSSProperties;
  onSelectDevice: (value: string) => void;
  onSelectApp: (value: string) => void;
  onSelectPackage: (value: string) => void;
  onSelectSuite: (value: string) => void;
  onRefreshSelectedDeviceStatus: () => void;
  onRefreshPackages: () => void;
  onRunTests: () => void;
  onStopCurrentTask: () => void;
  onSelectExecutionIndex: (index: number) => void;
  onAddSelectedCase: () => void;
  onAddAllCases: () => void;
  onRemoveSelectedCase: () => void;
  onMoveSelectedCaseUp: () => void;
  onMoveSelectedCaseDown: () => void;
  onClearExecutionPackages: () => void;
};

function RunnerTab({
  selectedDevice,
  selectedApp,
  selectedPackage,
  suite,
  deviceSelectOptions,
  appSelectOptions,
  packageSelectOptions,
  suiteOptions,
  isSelectedDeviceRunning,
  currentDevice,
  packageLabelMap,
  executionPackages,
  selectedExecutionIndex,
  summaryCardStyle,
  summaryBodyStyle,
  summaryValueStyle,
  onSelectDevice,
  onSelectApp,
  onSelectPackage,
  onSelectSuite,
  onRefreshSelectedDeviceStatus,
  onRefreshPackages,
  onRunTests,
  onStopCurrentTask,
  onSelectExecutionIndex,
  onAddSelectedCase,
  onAddAllCases,
  onRemoveSelectedCase,
  onMoveSelectedCaseUp,
  onMoveSelectedCaseDown,
  onClearExecutionPackages,
}: RunnerTabProps) {
  return (
    <Card title="选择设备并执行测试">
      <Row gutter={[12, 12]}>
        <Col span={6}>
          <label>测试设备</label>
          <Select style={{ width: "100%" }} value={selectedDevice} onChange={onSelectDevice} options={deviceSelectOptions} />
        </Col>
        <Col span={6}>
          <label>应用</label>
          <Select style={{ width: "100%" }} value={selectedApp} onChange={onSelectApp} options={appSelectOptions} />
        </Col>
        <Col span={6}>
          <label>可选用例</label>
          <Select
            style={{ width: "100%" }}
            value={selectedPackage}
            onChange={onSelectPackage}
            options={packageSelectOptions}
          />
        </Col>
        <Col span={6}>
          <label>测试范围</label>
          <Select style={{ width: "100%" }} value={suite} onChange={onSelectSuite} options={suiteOptions} />
        </Col>
      </Row>

      <Space style={{ marginTop: 12 }}>
        <Button htmlType="button" onClick={onRefreshSelectedDeviceStatus}>
          刷新设备状态
        </Button>
        <Button htmlType="button" onClick={onRefreshPackages}>
          刷新用例列表
        </Button>
        <Button htmlType="button" type="primary" onClick={onRunTests} disabled={isSelectedDeviceRunning}>
          开始执行
        </Button>
        <Button htmlType="button" danger onClick={onStopCurrentTask} disabled={!isSelectedDeviceRunning}>
          停止任务
        </Button>
      </Space>

      <TaskQueueCard
        executionPackages={executionPackages}
        selectedExecutionIndex={selectedExecutionIndex}
        packageLabelMap={packageLabelMap}
        onSelect={onSelectExecutionIndex}
        onAddSelected={onAddSelectedCase}
        onAddAll={onAddAllCases}
        onRemoveSelected={onRemoveSelectedCase}
        onMoveUp={onMoveSelectedCaseUp}
        onMoveDown={onMoveSelectedCaseDown}
        onClear={onClearExecutionPackages}
      />

      <DeviceSummaryCards
        currentDevice={currentDevice}
        summaryCardStyle={summaryCardStyle}
        summaryBodyStyle={summaryBodyStyle}
        summaryValueStyle={summaryValueStyle}
      />
    </Card>
  );
}

export default RunnerTab;
