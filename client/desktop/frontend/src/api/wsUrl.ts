import { useGatewayStore } from '../stores/gateway';

// wsUrl 构造经本地网关的 WS 地址。
// 浏览器 WebSocket 无法携带自定义 header，网关鉴权用查询参数 _token（middleware 对 WS 放行）。
export function wsUrl(path: string): string {
  const { config } = useGatewayStore.getState();
  const base = config?.baseURL ?? '';
  const token = config?.gatewayToken ?? '';
  const sep = path.includes('?') ? '&' : '?';
  return `${base.replace(/^http/, 'ws')}${path}${sep}_token=${encodeURIComponent(token)}`;
}

// bytesToBase64 浏览器端 Uint8Array → base64（分批避免栈溢出）。
export function bytesToBase64(bytes: Uint8Array): string {
  let bin = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    bin += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(bin);
}

export function base64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) {
    out[i] = bin.charCodeAt(i);
  }
  return out;
}