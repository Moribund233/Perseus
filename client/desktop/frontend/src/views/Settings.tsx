import { Card } from 'antd';
import { useTranslation } from 'react-i18next';
import { useGatewayStore } from '../stores/gateway';

export default function Settings() {
  const { t } = useTranslation();
  const config = useGatewayStore((s) => s.config);
  const tokenState = config?.gatewayToken ? t('desktop.settings.tokenGenerated') : t('desktop.settings.tokenMissing');
  return (
    <Card title={t('desktop.settings.title')} style={{ margin: 16 }}>
      <p>{t('desktop.settings.gateway')}: {config?.baseURL}</p>
      <p>{t('desktop.settings.token', { state: tokenState })}</p>
      <p className="muted">{t('desktop.settings.placeholder')}</p>
    </Card>
  );
}
