import { Card, Descriptions, Select, Space, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { useGatewayStore } from '../stores/gateway';
import { useServersStore } from '../stores/servers';
import { useWorkspaceStore } from '../stores/workspace';

const LANGUAGES = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
];

export default function Settings() {
  const { t, i18n } = useTranslation();
  const config = useGatewayStore((s) => s.config);
  const servers = useServersStore((s) => s.servers);
  const workspaces = useWorkspaceStore((s) => s.workspaces);
  const tokenState = config?.gatewayToken
    ? t('desktop.settings.tokenGenerated')
    : t('desktop.settings.tokenMissing');

  return (
    <div style={{ padding: 24, maxWidth: 760, margin: '0 auto', width: '100%' }}>
      <h2 style={{ fontSize: 20 }}>{t('desktop.settings.title')}</h2>
      <Space orientation="vertical" size="middle" style={{ width: '100%', marginTop: 16 }}>
        <Card size="small" title={t('desktop.settings.gatewayCard', { defaultValue: '本地网关' })}>
          <Descriptions column={1} size="small">
            <Descriptions.Item label={t('desktop.settings.gateway')}>
              {config?.baseURL ?? '—'}
            </Descriptions.Item>
            <Descriptions.Item label={t('desktop.settings.tokenLabel', { defaultValue: '网关会话 token' })}>
              {tokenState}
            </Descriptions.Item>
            <Descriptions.Item label={t('desktop.settings.workspaces', { defaultValue: '工作区数量' })}>
              {workspaces.length}
            </Descriptions.Item>
            <Descriptions.Item label={t('desktop.settings.serversCount', { defaultValue: '已注册服务器' })}>
              {servers.length}
            </Descriptions.Item>
          </Descriptions>
        </Card>
        <Card size="small" title={t('desktop.settings.language', { defaultValue: '语言 / Language' })}>
          <Select
            value={i18n.language.startsWith('zh') ? 'zh' : 'en'}
            options={LANGUAGES}
            style={{ width: 160 }}
            onChange={(lng) => void i18n.changeLanguage(lng)}
          />
        </Card>
        <Card size="small" title={t('desktop.settings.about', { defaultValue: '关于' })}>
          <Typography.Text type="secondary">
            Perseus Desktop — {t('desktop.settings.aboutDesc', { defaultValue: '远程 Perseus 客户端 + 本地工作区（Wails v2）' })}
          </Typography.Text>
        </Card>
      </Space>
    </div>
  );
}
