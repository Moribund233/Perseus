import { Row, Col, Card, Skeleton } from 'antd';

export default function RepositoriesSkeleton() {
  return (
    <div style={{ height: '100%' }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton.Button active key={i} style={{ width: 80 }} />
        ))}
      </div>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Skeleton active paragraph={{ rows: 10 }} />
          </Card>
        </Col>
        <Col span={18}>
          <Card>
            <Skeleton active paragraph={{ rows: 2 }} title={{ width: '50%' }} />
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} style={{ display: 'flex', gap: 12, padding: '12px 0', borderBottom: '1px solid #21262d' }}>
                <Skeleton.Avatar active size="small" shape="square" />
                <div style={{ flex: 1 }}>
                  <Skeleton active paragraph={{ rows: 1 }} title={{ width: '30%' }} />
                </div>
              </div>
            ))}
            <div style={{ marginTop: 24 }}>
              <Skeleton active paragraph={{ rows: 6 }} />
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
