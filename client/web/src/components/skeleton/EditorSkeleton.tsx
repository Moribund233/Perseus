import { Skeleton } from 'antd';

const treeWidths = [60, 45, 70, 50, 80, 55, 65, 75];
const lineWidths = [70, 55, 80, 60, 75, 50, 65, 85, 70, 60];

export default function EditorSkeleton() {
  return (
    <div style={{ display: 'flex', gap: 0, height: '100%' }}>
      <div style={{ width: 260, borderRight: '1px solid #21262d', padding: 16, flexShrink: 0 }}>
        <Skeleton.Input active style={{ width: '100%', marginBottom: 16 }} />
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, paddingLeft: i % 2 === 0 ? 20 : 0 }}>
            <Skeleton.Avatar active size="small" shape="square" />
            <Skeleton.Input active style={{ width: `${treeWidths[i - 1]}%`, height: 14 }} />
          </div>
        ))}
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', gap: 2, borderBottom: '1px solid #21262d', padding: '8px 16px' }}>
          {[1, 2, 3].map((i) => (
            <Skeleton.Button active key={i} style={{ width: 120 }} />
          ))}
        </div>
        <div style={{ flex: 1, padding: 16 }}>
          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((i) => (
            <div key={i} style={{ display: 'flex', gap: 16, marginBottom: 4, alignItems: 'center' }}>
              <Skeleton.Input active style={{ width: 30, height: 14 }} />
              <Skeleton.Input active style={{ width: `${lineWidths[i - 1]}%`, height: 14 }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
