import { ApiError } from '../../api/client';

/** 门禁预检结果：allowed=来源已放行（登录或进入）；source-denied=网关白名单拒绝；error=网络/服务异常 */
export type GatePhase = 'allowed' | 'source-denied' | 'error';

/**
 * 归类 `GET /api/app/status` 预检的失败原因：
 * - 403：网关来源白名单拒绝（此终端未授权），不应展示登录表单；
 * - 401：来源已放行但未登录，属正常流程，继续登录；
 * - 其它状态 / 网络异常：无法确认，提示重试。
 */
export function classifyGateError(err: unknown): GatePhase {
  if (err instanceof ApiError) {
    if (err.status === 403) return 'source-denied';
    if (err.status === 401) return 'allowed';
  }
  return 'error';
}
