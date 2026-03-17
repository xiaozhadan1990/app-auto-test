import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  List,
  message,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Typography,
} from "antd";
import type { CSSProperties, ReactNode } from "react";

type Device = {
  serial: string;
  status: string;
  brand: string;
  model: string;
  os_version: string;
  app_versions?: Record<string, string>;
};

type AppOption = {
  key: string;
  label: string;
};

type ApiOk = {
  ok: boolean;
  error?: string;
};

const svgModules = import.meta.glob("../assets/*.svg", {
  eager: true,
  import: "default",
}) as Record<string, string>;

const phoneSvgMap = Object.fromEntries(
  Object.entries(svgModules).map(([path, url]) => {
    const name = path.split("/").pop()?.replace(".svg", "").toLowerCase() || "";
    return [name, url];
  })
);

function normalizeKey(value?: string): string {
  return (value || "").toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function getBrandImageUrl(brand?: string): string | null {
  const key = normalizeKey(brand);
  if (!key) return null;
  if (phoneSvgMap[key]) return phoneSvgMap[key];
  return null;
}

function renderBrand(brand?: string, imageHeight = 36): ReactNode {
  const imageUrl = getBrandImageUrl(brand);
  if (imageUrl) {
    return (
      <img
        src={imageUrl}
        alt={brand || "phone-brand"}
        title={brand || ""}
        style={{ height: imageHeight, objectFit: "contain", display: "block" }}
      />
    );
  }
  return brand || "-";
}

function formatDeviceStatus(status?: string): string {
  const s = (status || "").toLowerCase();
  if (s === "device") return "已连接";
  if (s === "offline") return "离线";
  if (s === "unauthorized") return "未授权";
  if (s === "recovery") return "恢复模式";
  return status || "-";
}

async function apiRequest<T>(path: string, body?: unknown): Promise<T> {
  const resp = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }
  return (await resp.json()) as T;
}

function App() {
  const [msgApi, contextHolder] = message.useMessage();
  const [activeTab, setActiveTab] = useState("devices");
  const [devices, setDevices] = useState<Device[]>([]);
  const [apps, setApps] = useState<AppOption[]>([]);
  const [packages, setPackages] = useState<string[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>();
  const [selectedApp, setSelectedApp] = useState<string>();
  const [selectedPackage, setSelectedPackage] = useState<string>();
  const [suite, setSuite] = useState("all");
  const [executionPackages, setExecutionPackages] = useState<string[]>([]);
  const [selectedExecutionIndex, setSelectedExecutionIndex] = useState<number>(-1);
  const [logText, setLogText] = useState("等待执行...");
  const [startupMissing, setStartupMissing] = useState<string[]>([]);
  const summaryCardStyle: CSSProperties = { height: 132 };
  const summaryBodyStyle: CSSProperties = {
    minHeight: 86,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };
  const summaryValueStyle: CSSProperties = { fontSize: 26, fontWeight: 700, lineHeight: 1.1 };

  const currentDevice = useMemo(
    () => devices.find((d) => d.serial === selectedDevice),
    [devices, selectedDevice]
  );

  const refreshDevices = async () => {
    setLogText("正在刷新设备...");
    const res = await apiRequest<{ ok: boolean; devices: Device[]; error?: string }>(
      "/api/list_devices",
      {}
    );
    if (!res.ok) {
      setLogText(`刷新设备失败:\n${res.error || "unknown error"}`);
      return;
    }
    const list = res.devices || [];
    setDevices(list);
    if (list.length > 0) {
      setSelectedDevice((old) => old && list.some((d) => d.serial === old) ? old : list[0].serial);
    } else {
      setSelectedDevice(undefined);
      setLogText("未找到可用设备，请检查 adb devices。");
    }
  };

  const refreshApps = async () => {
    const res = await apiRequest<AppOption[]>("/api/get_app_options");
    setApps(res || []);
    if (res?.length) {
      setSelectedApp((old) => old && res.some((a) => a.key === old) ? old : res[0].key);
    }
  };

  const refreshPackages = async (appKey?: string) => {
    const targetApp = appKey || selectedApp;
    if (!targetApp) return;
    const res = await apiRequest<{ ok: boolean; packages: string[]; error?: string }>(
      "/api/list_test_packages",
      { app_key: targetApp }
    );
    if (!res.ok) {
      setLogText(`加载用例包失败:\n${res.error || "unknown error"}`);
      return;
    }
    const list = res.packages || [];
    setPackages(list);
    setSelectedPackage((old) => old && list.includes(old) ? old : list[0]);
    setExecutionPackages((old) => {
      const filtered = old.filter((p) => list.includes(p));
      return filtered.length ? filtered : (list[0] ? [list[0]] : []);
    });
    setSelectedExecutionIndex((old) => (old >= 0 ? old : (list.length ? 0 : -1)));
    setLogText("用例包已刷新。");
  };

  const addSelectedCase = () => {
    if (!selectedPackage) return;
    if (executionPackages.includes(selectedPackage)) {
      msgApi.info("该用例已在待执行列表中");
      setSelectedExecutionIndex(executionPackages.indexOf(selectedPackage));
      return;
    }
    const next = [...executionPackages, selectedPackage];
    setExecutionPackages(next);
    setSelectedExecutionIndex(next.length - 1);
  };

  const addAllCases = () => {
    let added = 0;
    let skipped = 0;
    const next = [...executionPackages];
    for (const p of packages) {
      if (next.includes(p)) {
        skipped += 1;
      } else {
        next.push(p);
        added += 1;
      }
    }
    setExecutionPackages(next);
    if (next.length) setSelectedExecutionIndex(next.length - 1);
    msgApi.info(`批量添加完成：新增 ${added}，跳过重复 ${skipped}`);
  };

  const removeSelectedCase = () => {
    if (selectedExecutionIndex < 0 || selectedExecutionIndex >= executionPackages.length) return;
    const next = executionPackages.filter((_, idx) => idx !== selectedExecutionIndex);
    setExecutionPackages(next);
    setSelectedExecutionIndex(Math.min(selectedExecutionIndex, next.length - 1));
  };

  const moveSelectedCase = (offset: number) => {
    const from = selectedExecutionIndex;
    const to = from + offset;
    if (from < 0 || from >= executionPackages.length) return;
    if (to < 0 || to >= executionPackages.length) return;
    const next = [...executionPackages];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    setExecutionPackages(next);
    setSelectedExecutionIndex(to);
  };

  const runTests = async () => {
    const appium = await apiRequest<{ running: boolean; server_url?: string; error?: string }>(
      "/api/appium_ready"
    );
    if (!appium.running) {
      const addr = appium.server_url || "http://127.0.0.1:4723";
      msgApi.error(`Appium 未启动（${addr}）`);
      setLogText(`执行已取消：Appium 未启动\n地址: ${addr}\n详情: ${appium.error || "unknown error"}`);
      setActiveTab("results");
      return;
    }
    if (!executionPackages.length) {
      msgApi.error("请先添加至少一个待执行用例");
      return;
    }
    if (!selectedDevice) {
      msgApi.error("请先选择手机设备");
      return;
    }
    if (!selectedApp) {
      msgApi.error("请先选择应用");
      return;
    }

    setActiveTab("results");
    setLogText(
      `正在执行测试，请稍候...\n执行顺序:\n${executionPackages
        .map((p, i) => `${i + 1}. ${p}`)
        .join("\n")}`
    );
    const res = await apiRequest<
      ApiOk & {
        pytest_exit_code?: number;
        allure_exit_code?: number;
        pytest_output?: string;
        allure_output?: string;
      }
    >("/api/run_tests", {
      device: selectedDevice,
      app_key: selectedApp,
      test_packages: executionPackages,
      suite,
    });
    if (!res.ok) {
      setLogText(
        `执行失败\n\n${res.error || res.pytest_output || "unknown error"}\n\n` +
          `pytest_output:\n${res.pytest_output || ""}\n\n` +
          `allure_output:\n${res.allure_output || ""}`
      );
    } else {
      setLogText(
        `执行完成\npytest_exit_code: ${res.pytest_exit_code}\nallure_exit_code: ${res.allure_exit_code}\n\n` +
          (res.pytest_output || "") +
          `\n\n--- Allure ---\n` +
          (res.allure_output || "")
      );
    }
  };

  const openReport = async () => {
    const res = await apiRequest<ApiOk>("/api/open_report", {});
    if (!res.ok) {
      msgApi.error(res.error || "打开报告失败");
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const startup = await apiRequest<{ missing_dependencies?: string[] }>("/api/startup_info");
        setStartupMissing(startup.missing_dependencies || []);
        await refreshApps();
        await refreshDevices();
      } catch (err) {
        setLogText(`页面初始化失败:\n${String(err)}`);
      }
    })();
  }, []);

  useEffect(() => {
    if (selectedApp) {
      refreshPackages(selectedApp);
    }
  }, [selectedApp]);

  return (
    <div style={{ width: "calc(100% - 24px)", maxWidth: "none", margin: "8px 12px 16px", padding: 0 }}>
      {contextHolder}
      <Typography.Title level={3} style={{ marginTop: 4 }}>
        移动自动化测试桌面端
      </Typography.Title>

      {startupMissing.length > 0 && (
        <Alert
          style={{ marginBottom: 12 }}
          type="warning"
          showIcon
          message={`系统缺少依赖: ${startupMissing.join(", ")}，请先安装并加入 PATH。`}
        />
      )}

      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            { key: "devices", label: "手机终端" },
            { key: "runner", label: "用例执行" },
            { key: "results", label: "执行结果" },
          ]}
        />
      </Card>

      {activeTab === "devices" && (
        <Card title="当前连接的手机终端">
          <Space style={{ marginBottom: 12 }}>
            <Button onClick={refreshDevices}>刷新设备</Button>
          </Space>
          <Table<Device>
            rowKey="serial"
            pagination={false}
            dataSource={devices}
            columns={[
              { title: "设备序列号", dataIndex: "serial" },
              { title: "状态", render: (_, d) => formatDeviceStatus(d.status) },
              {
                title: "品牌",
                render: (_, d) => renderBrand(d.brand, 32),
              },
              {
                title: "型号",
                dataIndex: "model",
              },
              { title: "系统", dataIndex: "os_version" },
              {
                title: "应用版本",
                render: (_, d) =>
                  `Lysora: ${(d.app_versions && d.app_versions.lysora) || "-"} / Ruijie: ${
                    (d.app_versions && d.app_versions.ruijieCloud) || "-"
                  }`,
              },
            ]}
          />
        </Card>
      )}

      {activeTab === "runner" && (
        <Card title="选择终端、测试用例并执行">
          <Row gutter={[12, 12]}>
            <Col span={6}>
              <label>手机设备</label>
              <Select
                style={{ width: "100%" }}
                value={selectedDevice}
                onChange={setSelectedDevice}
                options={devices.map((d) => ({ value: d.serial, label: `${d.serial} (${formatDeviceStatus(d.status)})` }))}
              />
            </Col>
            <Col span={6}>
              <label>应用</label>
              <Select
                style={{ width: "100%" }}
                value={selectedApp}
                onChange={setSelectedApp}
                options={apps.map((a) => ({ value: a.key, label: a.label }))}
              />
            </Col>
            <Col span={6}>
              <label>可选用例</label>
              <Select
                style={{ width: "100%" }}
                value={selectedPackage}
                onChange={setSelectedPackage}
                options={packages.map((p) => ({ value: p, label: p }))}
              />
            </Col>
            <Col span={6}>
              <label>测试范围</label>
              <Select
                style={{ width: "100%" }}
                value={suite}
                onChange={setSuite}
                options={[
                  { value: "all", label: "全部" },
                  { value: "smoke", label: "smoke" },
                  { value: "full", label: "full" },
                ]}
              />
            </Col>
          </Row>

          <Space style={{ marginTop: 12 }}>
            <Button onClick={() => refreshPackages()}>刷新用例包</Button>
            <Button type="primary" onClick={runTests}>
              启动执行
            </Button>
          </Space>

          <Card
            size="small"
            style={{ marginTop: 12, background: "#fafafa" }}
            title="待执行用例（按列表顺序执行）"
            extra={
              <Space wrap>
                <Button size="small" onClick={addSelectedCase}>
                  添加
                </Button>
                <Button size="small" onClick={addAllCases}>
                  添加全部
                </Button>
                <Button size="small" onClick={removeSelectedCase}>
                  移除
                </Button>
                <Button size="small" onClick={() => moveSelectedCase(-1)}>
                  上移
                </Button>
                <Button size="small" onClick={() => moveSelectedCase(1)}>
                  下移
                </Button>
                <Button
                  size="small"
                  onClick={() => {
                    setExecutionPackages([]);
                    setSelectedExecutionIndex(-1);
                  }}
                >
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
                  onClick={() => setSelectedExecutionIndex(idx)}
                  style={{
                    cursor: "pointer",
                    background: selectedExecutionIndex === idx ? "#e8f0fe" : undefined,
                  }}
                >
                  {idx + 1}. {item}
                </List.Item>
              )}
            />
          </Card>

          <Row gutter={10} style={{ marginTop: 12 }}>
            <Col span={5}>
              <Card size="small" title="手机品牌" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                {renderBrand(currentDevice?.brand, 56)}
              </Card>
            </Col>
            <Col span={5}>
              <Card size="small" title="设备型号" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                <span style={summaryValueStyle}>{currentDevice?.model || "-"}</span>
              </Card>
            </Col>
            <Col span={5}>
              <Card size="small" title="系统版本" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                <span style={summaryValueStyle}>{currentDevice?.os_version || "-"}</span>
              </Card>
            </Col>
            <Col span={4}>
              <Card size="small" title="Lysora 版本" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                <span style={summaryValueStyle}>
                  {(currentDevice?.app_versions && currentDevice.app_versions.lysora) || "-"}
                </span>
              </Card>
            </Col>
            <Col span={5}>
              <Card size="small" title="ruijieCloud 版本" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
                <span style={summaryValueStyle}>
                  {(currentDevice?.app_versions && currentDevice.app_versions.ruijieCloud) || "-"}
                </span>
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {activeTab === "results" && (
        <Card title="测试用例结果" extra={<Button onClick={openReport}>打开 Allure 报告</Button>}>
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
      )}
    </div>
  );
}

export default App;
