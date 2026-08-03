import { Row, Col, Card, Skeleton } from 'antd';

export default function DashboardSkeleton() {
  return (
    <div style={{ height: '100%', padding: 24 }}>
      <Skeleton.Input active style={{ width: 300, height: 32, marginBottom: 24 }} />
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {[1, 2, 3, 4].map((i) => (
          <Col span={6} key={i}>
            <Card>
              <Skeleton active paragraph={{ rows: 1 }} title={{ width: '60%' }} />
            </Card>
          </Col>
        ))}
      </Row>
      <Row gutter={[16, 16]}>
        <Col span={16}>
          <Card title={<Skeleton.Input active style={{ width: 120 }} />}>
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
                <Skeleton.Avatar active size="small" />
                <div style={{ flex: 1 }}>
                  <Skeleton active paragraph={{ rows: 1 }} title={{ width: '40%' }} />
                </div>
              </div>
            ))}
          </Card>
        </Col>
        <Col span={8}>
          <Card title={<Skeleton.Input active style={{ width: 100 }} />} style={{ marginBottom: 16 }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
                <Skeleton.Avatar active size="small" shape="square" />
                <Skeleton.Input active style={{ width: '70%', height: 14 }} />
              </div>
            ))}
          </Card>
          <Card title={<Skeleton.Input active style={{ width: 140 }} />}>
            <Skeleton active paragraph={{ rows: 4 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
