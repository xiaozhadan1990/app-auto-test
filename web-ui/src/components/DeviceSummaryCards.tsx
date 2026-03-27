import { Card, Col, Row } from "antd";
import type { CSSProperties } from "react";
import { renderBrand } from "../lib/appHelpers";
import type { Device } from "../types/app";

type DeviceSummaryCardsProps = {
  currentDevice?: Device;
  summaryCardStyle: CSSProperties;
  summaryBodyStyle: CSSProperties;
  summaryValueStyle: CSSProperties;
};

function DeviceSummaryCards({
  currentDevice,
  summaryCardStyle,
  summaryBodyStyle,
  summaryValueStyle,
}: DeviceSummaryCardsProps) {
  return (
    <Row gutter={10} style={{ marginTop: 12 }}>
      <Col span={4}>
        <Card size="small" title="手机品牌" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
          {renderBrand(currentDevice?.brand, 56)}
        </Card>
      </Col>
      <Col span={4}>
        <Card size="small" title="设备型号" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
          <span style={summaryValueStyle}>{currentDevice?.model || "-"}</span>
        </Card>
      </Col>
      <Col span={4}>
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
      <Col span={4}>
        <Card size="small" title="ruijieCloud 版本" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
          <span style={summaryValueStyle}>
            {(currentDevice?.app_versions && currentDevice.app_versions.ruijieCloud) || "-"}
          </span>
        </Card>
      </Col>
      <Col span={4}>
        <Card size="small" title="Reyee 版本" style={summaryCardStyle} styles={{ body: summaryBodyStyle }}>
          <span style={summaryValueStyle}>
            {(currentDevice?.app_versions && currentDevice.app_versions.reyee) || "-"}
          </span>
        </Card>
      </Col>
    </Row>
  );
}

export default DeviceSummaryCards;
