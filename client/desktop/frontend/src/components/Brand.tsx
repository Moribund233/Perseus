import Logo from './Logo';

// Perseus 品牌标记：英仙座流星雨（深色底反白版）。
export default function Brand({ size = 20 }: { size?: number }) {
  return <Logo size={size} variant="reverse" style={{ display: 'block' }} />;
}
