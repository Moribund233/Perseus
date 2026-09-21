import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Button, Input, Select } from 'antd';
import { ClearOutlined } from '@ant-design/icons';
import {
  formatStreamLine,
  logSocket,
  type LogSocketStatus,
  type StreamLogEntry,
} from '../../../api/logSocket';
import { LEVELS } from '../../../components/admin/logLine';
import VirtualLogBody from '../../../components/admin/VirtualLogBody';

/** 前端保留的实时日志上限，防止长时间订阅撑爆内存 */
const MAX_BUFFER = 5000;
const HISTORY_CHOICES = [50, 100, 200, 500];

const STATUS_CLASS: Record<LogSocketStatus, string> = {
  connecting: 'connecting',
  connected: 'on',
  disconnected: 'off',
};

/** 实时日志流 tab：订阅 /ws/logs，按级别/logger/关键字过滤并实时推送 */
export default function StreamLogTab() {
  const { t } = useTranslation();

  const [status, setStatus] = useState<LogSocketStatus>('connecting');
  const [entries, setEntries] = useState<StreamLogEntry[]>([]);
  const [levels, setLevels] = useState<string[]>([...LEVELS]);
  const [loggers, setLoggers] = useState<string[]>([]);
  const [keyword, setKeyword] = useState('');
  const [historyCount, setHistoryCount] = useState(100);
  const [follow, setFollow] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    logSocket.setHandlers({
      onHistory: (logs) => setEntries(logs.slice(-MAX_BUFFER)),
      onLog: (entry) => setEntries((prev) => [...prev, entry].slice(-MAX_BUFFER)),
      onStatusChange: setStatus,
      onError: (msg) => setError(msg),
    });
    logSocket.start({ levels: [...LEVELS] }, 100);
    return () => logSocket.stop();
  }, []);

  useEffect(() => {
    logSocket.updateFilters(
      { levels, loggers, keywords: keyword ? [keyword] : [] },
      historyCount,
    );
  }, [levels, loggers, keyword, historyCount]);

  const toggleLevel = (lv: string) => {
    setLevels((prev) => {
      const next = prev.includes(lv) ? prev.filter((x) => x !== lv) : [...prev, lv];
      return next.length ? next : [...LEVELS];
    });
  };

  const rows = useMemo(() => entries.map((e) => ({ text: formatStreamLine(e) })), [entries]);

  return (
    <div>
      <div className="ac-log-toolbar">
        <span className="ac-log-lab">{t('app.admin.logs.lines')}</span>
        <Select
          size="small"
          value={historyCount}
          onChange={setHistoryCount}
          options={HISTORY_CHOICES.map((n) => ({ label: String(n), value: n }))}
          style={{ width: 90 }}
        />
        <span className="ac-log-lab">{t('app.admin.logs.stream.logger')}</span>
        <Select
          size="small"
          mode="tags"
          value={loggers}
          onChange={setLoggers}
          placeholder={t('app.admin.logs.stream.loggerPlaceholder')}
          options={[]}
          style={{ minWidth: 180 }}
        />
        <Input.Search
          size="small"
          allowClear
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onSearch={setKeyword}
          placeholder={t('app.admin.logs.stream.keywordPlaceholder')}
          style={{ width: 200 }}
        />
        <button
          type="button"
          className={`ac-log-follow${follow ? ' on' : ''}`}
          onClick={() => setFollow((v) => !v)}
        >
          {follow ? t('app.admin.logs.followOn') : t('app.admin.logs.follow')}
        </button>
        <Button size="small" icon={<ClearOutlined />} onClick={() => setEntries([])}>
          {t('app.admin.logs.stream.clear')}
        </Button>
        <div className="ac-log-filters">
          {LEVELS.map((lv) => (
            <button
              key={lv}
              type="button"
              className={`ac-fchip${levels.includes(lv) ? ' on' : ''}`}
              data-level={lv.toLowerCase()}
              onClick={() => toggleLevel(lv)}
            >
              {lv}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <Alert
          type="error"
          showIcon
          message={t('app.admin.logs.loadFailed')}
          description={error}
          style={{ marginBottom: 18 }}
        />
      )}

      <div className={`ac-log-term${follow ? ' live' : ''}`}>
        <div className="ac-log-cap">
          <span className="ac-log-path">{t('app.admin.logs.stream.channel')}</span>
          <span className="ac-log-count">
            {t('app.admin.logs.count', { shown: entries.length, total: entries.length })}
          </span>
          <span className={`ac-log-state ${STATUS_CLASS[status]}`}>
            {t(`app.admin.logs.stream.${status}`)}
          </span>
        </div>
        <VirtualLogBody
          rows={rows}
          follow={follow}
          emptyText={t('app.admin.logs.stream.waiting')}
        />
      </div>
    </div>
  );
}
