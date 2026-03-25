import { Button, Card, List, Space } from "antd";
import { resolvePackageLabel } from "../lib/appHelpers";

type TaskQueueCardProps = {
  executionPackages: string[];
  selectedExecutionIndex: number;
  packageLabelMap: Record<string, string>;
  onSelect: (index: number) => void;
  onAddSelected: () => void;
  onAddAll: () => void;
  onRemoveSelected: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onClear: () => void;
};

function TaskQueueCard({
  executionPackages,
  selectedExecutionIndex,
  packageLabelMap,
  onSelect,
  onAddSelected,
  onAddAll,
  onRemoveSelected,
  onMoveUp,
  onMoveDown,
  onClear,
}: TaskQueueCardProps) {
  return (
    <Card
      size="small"
      style={{ marginTop: 12, background: "#fafafa" }}
      title="待执行用例（按顺序执行）"
      extra={
        <Space wrap>
          <Button size="small" onClick={onAddSelected}>
            添加
          </Button>
          <Button size="small" onClick={onAddAll}>
            全部添加
          </Button>
          <Button size="small" onClick={onRemoveSelected}>
            移除
          </Button>
          <Button size="small" onClick={onMoveUp}>
            上移
          </Button>
          <Button size="small" onClick={onMoveDown}>
            下移
          </Button>
          <Button size="small" onClick={onClear}>
            清空
          </Button>
        </Space>
      }
    >
      <List
        bordered
        dataSource={executionPackages}
        renderItem={(item, idx) => (
          <List.Item
            onClick={() => onSelect(idx)}
            style={{
              cursor: "pointer",
              background: selectedExecutionIndex === idx ? "#e8f0fe" : undefined,
            }}
          >
            {idx + 1}. {resolvePackageLabel(item, packageLabelMap)}
          </List.Item>
        )}
      />
    </Card>
  );
}

export default TaskQueueCard;
