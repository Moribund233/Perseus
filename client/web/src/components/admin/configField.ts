/**
 * 配置字段的呈现元数据：由当前值类型推断控件形态，并标注「只读」字段。
 * 只读规则与后端 config_service 对齐：
 *   - 受保护节（storage/security/app/logging/system 等）：整节只读
 *   - server.reload / database.url / database.is_stress_test：字段级只读
 */

export type ConfigValue = string | number | boolean | string[] | null;

/** 后端允许修改的配置节（config_service.ALLOWED_CONFIG_SECTIONS） */
export const EDITABLE_SECTIONS = ['server', 'gunicorn', 'proxy', 'cors', 'database'] as const;

/** 字段级只读（后端拒绝修改并返回明确错误） */
export const READONLY_FIELDS: Record<string, string[]> = {
  server: ['reload'],
  database: ['url', 'is_stress_test'],
};

export type FieldType = 'bool' | 'int' | 'str' | 'list' | 'null';

export function fieldTypeOf(value: unknown): FieldType {
  if (typeof value === 'boolean') return 'bool';
  if (typeof value === 'number') return Number.isInteger(value) ? 'int' : 'str';
  if (Array.isArray(value)) return value.every((v) => typeof v === 'string') ? 'list' : 'null';
  if (typeof value === 'string') return 'str';
  return 'null';
}

export function isEditableSection(section: string): boolean {
  return (EDITABLE_SECTIONS as readonly string[]).includes(section);
}

export function isReadonlyField(section: string, field: string): boolean {
  return (READONLY_FIELDS[section] ?? []).includes(field);
}

/** 枚举字段 → 下拉选项；非枚举字符串保持文本输入 */
export const ENUM_FIELDS: Record<string, Record<string, string[]>> = {
  server: {
    log_level: ['debug', 'info', 'warning', 'error', 'critical'],
  },
  database: {
    pg_ssl_mode: ['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'],
  },
};

export function enumOptionsOf(section: string, field: string): string[] | null {
  return ENUM_FIELDS[section]?.[field] ?? null;
}

/** 列表字段的行分隔显示（textarea 一值一行） */
export function listToString(value: string[]): string {
  return value.join('\n');
}

export function stringToList(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((v) => v.trim())
    .filter(Boolean);
}

export function toPayloadValue(current: unknown, raw: string): unknown {
  const type = fieldTypeOf(current);
  if (type === 'bool') return raw === 'true' || raw === '1' || raw.toLowerCase() === 'on';
  if (type === 'int') {
    const n = Number(raw.trim());
    return Number.isFinite(n) ? Math.trunc(n) : raw;
  }
  if (type === 'list') return stringToList(raw);
  return raw;
}