import { Button, Card, Space, Table } from "antd";
import type { TableProps } from "antd";
import type { Device } from "../types/app";

type DevicesTabProps = {
  devices: Device[];
  deviceTableColumns: TableProps<Device>["columns"];
  onRefresh: () => void;
};

function DevicesTab({ devices, deviceTableColumns, onRefresh }: DevicesTabProps) {
  return (
    <Card title="当前连接的手机终端">
      <Space style={{ marginBottom: 12 }}>
        <Button onClick={onRefresh}>刷新设备</Button>
      </Space>
      <Table rowKey="serial" pagination={false} dataSource={devices} columns={deviceTableColumns} />
    </Card>
  );
}

export default DevicesTab;
