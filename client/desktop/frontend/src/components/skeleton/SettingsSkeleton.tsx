import { Card, Skeleton } from 'antd';

export default function SettingsSkeleton() {
  return (
    <div style={{ maxWidth: 720, height: '100%' }}>
      {[1, 2, 3].map((i) => (
        <Card key={i} style={{ marginBottom: 16 }}>
          <Skeleton active paragraph={{ rows: 2 }} title={{ width: '30%' }} />
          <div style={{ marginTop: 16 }}>
            <Skeleton.Input active style={{ width: '100%', height: 36, marginBottom: 12 }} />
            <Skeleton.Input active style={{ width: '100%', height: 36, marginBottom: 12 }} />
            <Skeleton.Button active style={{ width: 100 }} />
          </div>
        </Card>
      ))}
    </div>
  );
}
