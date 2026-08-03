import { Card } from 'antd';
import { useGatewayStore } from '../stores/gateway';

export default function Settings() {
  const config = useGatewayStore((s) => s.config);
  return (
    <Card title="设置" style={{ margin: 16 }}>
      <p>网关地址: {config?.baseURL}</p>
      <p>会话 token: {config?.gatewayToken ? '已生成（仅内存）' : '未生成'}</p>
      <p className="muted">Phase 1 占位。数据目录持久化、主题、SSH 密钥等在后续阶段实现。</p>
    </Card>
  );
}
