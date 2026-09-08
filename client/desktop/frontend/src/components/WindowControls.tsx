import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BorderOutlined, CloseOutlined, MinusOutlined, SwitcherOutlined } from '@ant-design/icons';

// 自定义标题栏的窗口控制（Frameless 模式）。
// 直接走 window.runtime（Wails 注入），与 window.go 的用法保持一致。

export default function WindowControls() {
  const { t } = useTranslation();
  const [maximised, setMaximised] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  const sync = () => {
    if (!window.runtime) return;
    void window.runtime
      .WindowIsMaximised()
      .then(setMaximised)
      .catch(() => {});
  };

  useEffect(() => {
    sync();
    const onResize = () => {
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(sync, 150);
    };
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      window.clearTimeout(timer.current);
    };
  }, []);

  const toggleMaximise = () => {
    if (!window.runtime) return;
    window.runtime.WindowToggleMaximise();
    window.setTimeout(sync, 250);
  };

  return (
    <div className="win-controls">
      <button className="wc-btn" title={t('desktop.window.minimize')} onClick={() => window.runtime?.WindowMinimise()}>
        <MinusOutlined />
      </button>
      <button
        className="wc-btn"
        title={maximised ? t('desktop.window.restore') : t('desktop.window.maximize')}
        onClick={toggleMaximise}
      >
        {maximised ? <SwitcherOutlined /> : <BorderOutlined />}
      </button>
      <button className="wc-btn closer" title={t('desktop.window.close')} onClick={() => window.runtime?.Quit()}>
        <CloseOutlined />
      </button>
    </div>
  );
}