import { describe, it, expect } from 'vitest';
import { ApiError } from '../../api/client';
import { classifyGateError } from './gate';

describe('classifyGateError', () => {
  it('403 → source-denied（网关白名单拒绝）', () => {
    expect(classifyGateError(new ApiError(403, 'forbidden'))).toBe('source-denied');
  });

  it('401 → allowed（来源已放行，待登录）', () => {
    expect(classifyGateError(new ApiError(401, 'unauthorized'))).toBe('allowed');
  });

  it('5xx → error', () => {
    expect(classifyGateError(new ApiError(500, 'boom'))).toBe('error');
  });

  it('网络异常 → error', () => {
    expect(classifyGateError(new TypeError('fetch failed'))).toBe('error');
  });
});
