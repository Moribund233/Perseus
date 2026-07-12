import { Skeleton, Card } from 'antd';

export default function PullRequestsSkeleton() {
  return (
    <div style={{ height: '100%' }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {[1, 2, 3].map((i) => (
          <Skeleton.Button active key={i} style={{ width: 100 }} />
        ))}
      </div>
      <Card>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} style={{ display: 'flex', gap: 12, padding: '16px 0', borderBottom: '1px solid #21262d' }}>
            <Skeleton.Avatar active size="small" />
            <div style={{ flex: 1 }}>
              <Skeleton active paragraph={{ rows: 1 }} title={{ width: '60%' }} />
            </div>
            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <Skeleton.Avatar active size="small" shape="circle" />
              <Skeleton.Avatar active size="small" shape="circle" />
              <Skeleton.Avatar active size="small" shape="circle" />
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}
