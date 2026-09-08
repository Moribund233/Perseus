import { NodeIndexOutlined } from '@ant-design/icons';

// Perseus 品牌标记：渐变圆角底 + 节点图标。
export default function Brand({ size = 20 }: { size?: number }) {
  return (
    <span
      className="brand-mark"
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.28,
        fontSize: size * 0.6,
      }}
    >
      <NodeIndexOutlined />
    </span>
  );
}