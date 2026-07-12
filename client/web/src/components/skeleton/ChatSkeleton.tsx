import { Skeleton } from 'antd';

export default function ChatSkeleton() {
  return (
    <div style={{ display: 'flex', gap: 0, height: '100%' }}>
      <div style={{ width: 240, borderRight: '1px solid #21262d', padding: 16, flexShrink: 0 }}>
        <Skeleton.Input active style={{ width: '100%', marginBottom: 16, height: 28 }} />
        <div style={{ marginBottom: 16 }}>
          <Skeleton.Input active style={{ width: 80, height: 14, marginBottom: 8 }} />
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
              <Skeleton.Avatar active size="small" />
              <Skeleton.Input active style={{ width: '60%', height: 14 }} />
            </div>
          ))}
        </div>
        <div>
          <Skeleton.Input active style={{ width: 60, height: 14, marginBottom: 8 }} />
          {[1, 2, 3, 4].map((i) => (
            <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
              <Skeleton.Avatar active size="small" />
              <Skeleton.Input active style={{ width: '50%', height: 14 }} />
            </div>
          ))}
        </div>
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: 16, borderBottom: '1px solid #21262d' }}>
          <Skeleton.Input active style={{ width: 200, height: 20 }} />
        </div>
        <div style={{ flex: 1, padding: 16 }}>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
              <Skeleton.Avatar active />
              <div style={{ flex: 1 }}>
                <Skeleton active paragraph={{ rows: 2 }} title={{ width: '30%' }} />
              </div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ width: 220, borderLeft: '1px solid #21262d', padding: 16, flexShrink: 0 }}>
        <Skeleton.Input active style={{ width: 80, height: 14, marginBottom: 12 }} />
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
            <Skeleton.Avatar active size="small" />
            <Skeleton.Input active style={{ width: '60%', height: 14 }} />
          </div>
        ))}
      </div>
    </div>
  );
}
