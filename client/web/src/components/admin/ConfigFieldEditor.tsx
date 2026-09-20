import { useTranslation } from 'react-i18next';
import { Input, InputNumber, Select, Switch } from 'antd';
import {
  enumOptionsOf,
  fieldTypeOf,
  listToString,
  stringToList,
} from './configField';

interface ConfigFieldEditorProps {
  section: string;
  field: string;
  value: unknown;
  readonly?: boolean;
  onChange: (value: unknown) => void;
}

/**
 * 单个配置字段的编辑控件。
 * 根据当前值的类型自动选择控件：bool → Switch, int → InputNumber, str → Input/Select, list → textarea。
 */
export default function ConfigFieldEditor({
  section,
  field,
  value,
  readonly,
  onChange,
}: ConfigFieldEditorProps) {
  const { t } = useTranslation();
  const type = fieldTypeOf(value);
  const options = enumOptionsOf(section, field);
  const dataTestId = `cfg-${section}-${field}`;

  if (readonly) {
    return (
      <div className="ac-cfg-ro" data-testid={`${dataTestId}-ro`}>
        <pre>{typeof value === 'string' ? value : JSON.stringify(value)}</pre>
      </div>
    );
  }

  if (type === 'bool') {
    return (
      <Switch
        size="small"
        checked={value === true}
        onChange={(checked) => onChange(checked)}
        data-testid={dataTestId}
      />
    );
  }

  if (type === 'int') {
    return (
      <InputNumber
        size="small"
        value={value as number}
        onChange={(v) => onChange(v)}
        data-testid={dataTestId}
      />
    );
  }

  if (type === 'list') {
    const text = listToString(value as string[]);
    return (
      <Input.TextArea
        rows={Math.min(6, Math.max(2, (value as string[]).length))}
        value={text}
        autoSize={{ minRows: 2, maxRows: 8 }}
        onChange={(e) => onChange(stringToList(e.target.value))}
        data-testid={dataTestId}
        placeholder={t('app.admin.config.field.listHint')}
      />
    );
  }

  if (type === 'str') {
    const current = value as string;
    if (options) {
      return (
        <Select
          size="small"
          value={current}
          style={{ minWidth: 160 }}
          options={options.map((o) => ({ value: o, label: o }))}
          onChange={(v) => onChange(v)}
          data-testid={dataTestId}
        />
      );
    }
    return (
      <Input
        size="small"
        value={current}
        onChange={(e) => onChange(e.target.value)}
        data-testid={dataTestId}
      />
    );
  }

  return (
    <div className="ac-cfg-ro" data-testid={`${dataTestId}-ro`}>
      <pre>{value === null ? 'null' : JSON.stringify(value)}</pre>
    </div>
  );
}