import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, App, Button } from 'antd';
import { ReloadOutlined, SaveOutlined, ClearOutlined } from '@ant-design/icons';
import { configApi, type ConfigData } from '../../../api/admin';
import KeyValueLedger from '../../../components/admin/KeyValueLedger';
import ConfigFieldEditor from '../../../components/admin/ConfigFieldEditor';
import ConfirmDangerModal from '../../../components/admin/ConfirmDangerModal';
import AdminSkeleton from '../../../components/admin/AdminSkeleton';
import {
  EDITABLE_SECTIONS,
  isEditableSection,
  isReadonlyField,
  type ConfigValue,
} from '../../../components/admin/configField';

type DraftMap = Record<string, Record<string, ConfigValue>>;

interface Feedback {
  kind: 'ok' | 'error';
  title: string;
  lines: string[];
}

const RESET_CONFIRM_WORD = 'RESET';

function formatDisplay(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}

/** 从后端返回的全量配置构建可编辑草稿（仅编辑节的「非只读字段」） */
function buildDraft(data: ConfigData): DraftMap {
  const draft: DraftMap = {};
  for (const section of EDITABLE_SECTIONS) {
    const sectionData = data[section];
    if (!sectionData || typeof sectionData !== 'object') continue;
    const fields: Record<string, ConfigValue> = {};
    for (const [field, value] of Object.entries(sectionData)) {
      if (isReadonlyField(section, field)) continue;
      fields[field] = value as ConfigValue;
    }
    draft[section] = fields;
  }
  return draft;
}

function buildPayload(draft: DraftMap, sections: string[]): ConfigData {
  const payload: ConfigData = {};
  for (const section of sections) {
    if (!draft[section]) continue;
    payload[section] = { ...draft[section] };
  }
  return payload;
}

export default function ConfigSection() {
  const { t } = useTranslation();
  const { message } = App.useApp();

  const [raw, setRaw] = useState<ConfigData | null>(null);
  const [draft, setDraft] = useState<DraftMap>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validateOut, setValidateOut] = useState<{ success: boolean; errors: string[] } | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [resetOpen, setResetOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<string>(EDITABLE_SECTIONS[0]);

  const load = useCallback(async () => {
    const res = await configApi.getConfig();
    if (!res.data) {
      setLoadError(t('app.admin.config.loadEmpty'));
      return;
    }
    setRaw(res.data);
    setDraft(buildDraft(res.data));
    setLoadError(null);
    setValidateOut(null);
    setFeedback(null);
  }, [t]);

  useEffect(() => {
    let cancelled = false;
    configApi.getConfig()
      .then((res) => {
        if (cancelled) return;
        if (!res.data) {
          setLoadError(t('app.admin.config.loadEmpty'));
          return;
        }
        setRaw(res.data);
        setDraft(buildDraft(res.data));
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [t]);

  /** 相对原始配置的脏字段（section.field） */
  const dirtyKeys = useMemo(() => {
    if (!raw) return [];
    const keys: string[] = [];
    for (const [section, fields] of Object.entries(draft)) {
      const base = raw[section] ?? {};
      for (const [field, value] of Object.entries(fields)) {
        if (JSON.stringify(base[field]) !== JSON.stringify(value)) {
          keys.push(`${section}.${field}`);
        }
      }
    }
    return keys;
  }, [raw, draft]);

  const dirtySections = useMemo(() => {
    const set = new Set<string>();
    for (const key of dirtyKeys) set.add(key.split('.')[0]);
    return [...set];
  }, [dirtyKeys]);

  const handleChange = (section: string, field: string, value: unknown) => {
    setDraft((prev) => ({
      ...prev,
      [section]: { ...prev[section], [field]: value as ConfigValue },
    }));
    setValidateOut(null);
  };

  const sectionsOrdered = useMemo(() => {
    if (!raw) return { editable: [] as string[], readonly: [] as string[] };
    const editable = EDITABLE_SECTIONS.filter((s) => raw[s] && typeof raw[s] === 'object');
    const readonly = Object.keys(raw).filter((s) => !isEditableSection(s));
    return { editable, readonly };
  }, [raw]);

  const validate = async () => {
    setValidating(true);
    try {
      const payload = buildPayload(draft, [...EDITABLE_SECTIONS]);
      const res = await configApi.validateConfig(payload);
      setValidateOut({ success: res.success, errors: res.errors ?? [] });
    } catch (err) {
      setValidateOut({ success: false, errors: [err instanceof Error ? err.message : String(err)] });
    } finally {
      setValidating(false);
    }
  };

  const save = async () => {
    if (dirtySections.length === 0) return;
    setBusy(true);
    try {
      const res = await configApi.updateConfig(buildPayload(draft, dirtySections));
      if (res.success) {
        message.success(t('app.admin.config.save.saved'));
        const hints = res.hints ?? [];
        setFeedback(
          hints.length > 0
            ? { kind: 'ok', title: t('app.admin.config.save.saved'), lines: hints }
            : null,
        );
      } else {
        setFeedback({ kind: 'error', title: t('app.admin.config.save.failed'), lines: res.errors ?? [] });
      }
      await load();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      message.error(msg);
      setFeedback({ kind: 'error', title: t('app.admin.config.save.failed'), lines: [msg] });
    } finally {
      setBusy(false);
    }
  };

  const doReset = async () => {
    setBusy(true);
    try {
      const res = await configApi.resetConfig();
      if (res.success) {
        message.success(t('app.admin.config.reset.done'));
        setFeedback({ kind: 'ok', title: t('app.admin.config.reset.done'), lines: [] });
        await load();
      } else {
        setFeedback({ kind: 'error', title: t('app.admin.config.reset.failed'), lines: res.errors ?? [] });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      message.error(msg);
      setFeedback({ kind: 'error', title: t('app.admin.config.reset.failed'), lines: [msg] });
    } finally {
      setBusy(false);
      setResetOpen(false);
    }
  };

  const sectionList = useMemo(() => [...sectionsOrdered.editable, ...sectionsOrdered.readonly], [sectionsOrdered]);

  return (
    <div>
      <div className="ac-page-head">
        <div>
          <h1 className="ac-h1">{t('app.admin.config.title')}</h1>
          <div className="ac-sub">{t('app.admin.config.subtitle')}</div>
        </div>
        <div className="ac-toolbar">
          {dirtyKeys.length > 0 && (
            <span className="ac-chip warn">{t('app.admin.config.dirty', { count: dirtyKeys.length })}</span>
          )}
          <Button size="small" icon={<ReloadOutlined />} onClick={() => void load()}>
            {t('app.admin.config.refresh')}
          </Button>
          <Button size="small" loading={validating} onClick={() => void validate()}>
            {t('app.admin.config.runValidate')}
          </Button>
          <Button
            size="small"
            type="primary"
            icon={<SaveOutlined />}
            disabled={dirtySections.length === 0}
            loading={busy}
            onClick={() => void save()}
          >
            {t('app.admin.config.save.button')}
          </Button>
        </div>
      </div>

      {loadError && <Alert type="error" showIcon message={t('app.admin.config.loadFailed')} description={loadError} style={{ marginBottom: 18 }} />}

      {!raw && !loadError && <AdminSkeleton heading={t('app.admin.config.title')} rows={6} />}

      {feedback && (
        <div className={`ac-banner ${feedback.kind === 'ok' ? '' : 'danger'}`}>
          <div>
            <div className="ac-banner-title">{feedback.title}</div>
            {feedback.lines.length > 0 && (
              <div className="ac-banner-desc">
                {feedback.lines.map((line) => <div key={line}>{line}</div>)}
              </div>
            )}
          </div>
        </div>
      )}

      {validateOut && (
        <div className={`ac-banner ${validateOut.success ? '' : 'danger'}`}>
          <div>
            <div className="ac-banner-title">
              {validateOut.success ? t('app.admin.config.validate.ok') : t('app.admin.config.validate.bad')}
            </div>
            {validateOut.errors.length > 0 && (
              <div className="ac-banner-desc">
                {validateOut.errors.map((line) => <div key={line}>{line}</div>)}
              </div>
            )}
          </div>
        </div>
      )}

      {raw && (
        <>
          <div className="ac-cfg-nav">
            {sectionList.map((section) => {
              const isEditable = isEditableSection(section);
              const dirtyCount = dirtyKeys.filter((k) => k.startsWith(`${section}.`)).length;
              return (
                <button
                  key={section}
                  type="button"
                  className={`ac-cfg-sect${activeSection === section ? ' active' : ''}`}
                  onClick={() => setActiveSection(section)}
                >
                  <span className="ac-cfg-sect-name">{section}</span>
                  {isEditable ? (
                    dirtyCount > 0 ? (
                      <span className="ac-cfg-dirty">{dirtyCount}</span>
                    ) : (
                      <span className="ac-cfg-dot" />
                    )
                  ) : (
                    <span className="ac-cfg-lock" />
                  )}
                </button>
              );
            })}
          </div>

          <div className="ac-panel">
            <div className="ac-panel-head">
              {activeSection}
              {isEditableSection(activeSection) ? (
                <span className="ac-chip info">{t('app.admin.config.editable')}</span>
              ) : (
                <span className="ac-chip warn">{t('app.admin.config.protected')}</span>
              )}
            </div>
            <div className="ac-panel-body">
              {isEditableSection(activeSection) ? (
                <div className="ac-cfg-form">
                  {Object.entries(raw[activeSection] ?? {}).map(([field, value]) => {
                    const readonly = isReadonlyField(activeSection, field);
                    return (
                      <div className="ac-cfg-row" key={field}>
                        <span className="ac-cfg-name">
                          <code>{field}</code>
                          {readonly ? (
                            <span className="ac-cfg-ro-badge">{t('app.admin.config.readonly')}</span>
                          ) : (
                            dirtyKeys.includes(`${activeSection}.${field}`) && <span className="ac-cfg-dirty-badge" />
                          )}
                        </span>
                        <div className="ac-cfg-control">
                          {readonly ? (
                            <div className="ac-cfg-val-ro">{formatDisplay(value)}</div>
                          ) : (
                            <ConfigFieldEditor
                              section={activeSection}
                              field={field}
                              value={value}
                              onChange={(v) => handleChange(activeSection, field, v)}
                            />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <KeyValueLedger
                  rows={Object.entries(raw[activeSection] ?? {}).map(([field, value]) => ({
                    key: field,
                    label: field,
                    value: <span className="ac-cfg-val-ro">{formatDisplay(value)}</span>,
                  }))}
                />
              )}
            </div>
          </div>

          <div className="ac-cfg-reset">
            <Button
              danger
              size="small"
              icon={<ClearOutlined />}
              loading={busy}
              onClick={() => setResetOpen(true)}
            >
              {t('app.admin.config.reset.button')}
            </Button>
          </div>
        </>
      )}

      <ConfirmDangerModal
        open={resetOpen}
        title={t('app.admin.config.reset.title')}
        description={t('app.admin.config.reset.desc')}
        confirmWord={RESET_CONFIRM_WORD}
        actionLabel={t('app.admin.config.reset.confirmAction')}
        busy={busy}
        onAction={() => void doReset()}
        onClose={() => setResetOpen(false)}
      />
    </div>
  );
}