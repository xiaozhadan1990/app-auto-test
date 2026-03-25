import { Alert } from "antd";

type StartupAlertProps = {
  startupMissing: string[];
};

function StartupAlert({ startupMissing }: StartupAlertProps) {
  if (startupMissing.length === 0) {
    return null;
  }

  return (
    <Alert
      style={{ marginBottom: 12 }}
      type="warning"
      showIcon
      message={`系统缺少依赖：${startupMissing.join("、")}，请先安装并加入 PATH。`}
    />
  );
}

export default StartupAlert;
