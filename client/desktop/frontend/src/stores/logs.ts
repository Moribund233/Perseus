import { create } from 'zustand';

export type LogKind = 'info' | 'ok' | 'err' | 'lsp' | 'git';

export interface LogLine {
  time: string;
  text: string;
  kind?: LogKind;
}

const MAX_LINES = 500;

function nowTime(): string {
  return new Date().toTimeString().slice(0, 8);
}

// 输出面板日志：网关 / 服务器 / LSP / Git 操作的时间线。
export const useLogsStore = create<{
  lines: LogLine[];
  append: (text: string, kind?: LogKind) => void;
  clear: () => void;
}>((set) => ({
  lines: [],
  append: (text, kind) =>
    set((s) => ({
      lines: [...s.lines.slice(-(MAX_LINES - 1)), { time: nowTime(), text, kind }],
    })),
  clear: () => set({ lines: [] }),
}));

export function logInfo(text: string) {
  useLogsStore.getState().append(text, 'info');
}
export function logOk(text: string) {
  useLogsStore.getState().append(text, 'ok');
}
export function logErr(text: string) {
  useLogsStore.getState().append(text, 'err');
}
export function logLsp(text: string) {
  useLogsStore.getState().append(text, 'lsp');
}
export function logGit(text: string) {
  useLogsStore.getState().append(text, 'git');
}