import { Button, Result, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

/**
 * 网关初始化失败错误页
 *
 * 展示错误概要 + 可复制的详细堆栈, 提供重试入口。
 * 常见原因: 网关未就绪 (wails dev 下前端先于后端请求)、端口被占、
 * dev server origin 未放行 (CORS 预检失败表现为 "Failed to fetch")。
 */
export default function ErrorPage({ error }: { error: string }) {
  const { t } = useTranslation();
  return (
    <div className="error-page">
      <Result
        status="error"
        title={t('desktop.app.errorTitle', { defaultValue: '无法连接本地网关' })}
        subTitle={t('desktop.app.errorDesc', {
          defaultValue: 'Perseus 桌面端依赖本地网关进程。请确认没有旧实例占用端口, 然后重试。',
        })}
        extra={
          <Button type="primary" icon={<ReloadOutlined />} onClick={() => window.location.reload()}>
            {t('desktop.app.retry', { defaultValue: '重试' })}
          </Button>
        }
      >
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
          {t('desktop.app.errorDetail', { defaultValue: '错误详情' })}:
        </Typography.Paragraph>
        <Typography.Paragraph>
          <Typography.Text code copyable style={{ display: 'block', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            {error}
          </Typography.Text>
        </Typography.Paragraph>
      </Result>
    </div>
  );
}
