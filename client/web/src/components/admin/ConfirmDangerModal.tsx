import { useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Modal, Input } from 'antd';

interface ConfirmDangerModalProps {
  open: boolean;
  title: string;
  description: string;
  /** 识别危险操作的确认词（区分大小写） */
  confirmWord: string;
  actionLabel: string;
  busy?: boolean;
  /** 描述与确认输入之间的附加控件（如可调参数） */
  extra?: ReactNode;
  onAction: () => void;
  onClose: () => void;
}

/**
 * 危险操作确认弹窗：必须输入确认词才能执行。
 * 配合文案「输入 {{word}} 以继续」使用，避免二次确认被随手点过。
 */
export default function ConfirmDangerModal({
  open,
  title,
  description,
  confirmWord,
  actionLabel,
  busy,
  extra,
  onAction,
  onClose,
}: ConfirmDangerModalProps) {
  const { t } = useTranslation();
  const [typed, setTyped] = useState('');

  const matched = typed.trim() === confirmWord;

  const handleClose = () => {
    setTyped('');
    onClose();
  };

  const handleAction = () => {
    if (!matched || busy) return;
    setTyped('');
    onAction();
  };

  return (
    <Modal
      open={open}
      title={title}
      onCancel={handleClose}
      onOk={handleAction}
      okText={actionLabel}
      cancelText={t('common.cancel')}
      okButtonProps={{ danger: true, disabled: !matched, loading: busy }}
      centered
    >
      <div className="ac-danger-desc">{description}</div>
      {extra && <div className="ac-danger-extra">{extra}</div>}
      <div className="ac-danger-field">
        <div className="ac-danger-label">{t('app.admin.danger.typeToConfirm', { word: confirmWord })}</div>
        <Input
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          placeholder={confirmWord}
          onPressEnter={handleAction}
        />
      </div>
    </Modal>
  );
}