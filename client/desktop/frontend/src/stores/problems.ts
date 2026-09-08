import { create } from 'zustand';

export interface Position {
  line: number;
  character: number;
}

export interface Range {
  start: Position;
  end: Position;
}

export interface Diagnostic {
  uri: string;
  range: Range;
  severity: number;
  message: string;
  source?: string;
  code?: string | number;
}

interface ProblemsState {
  diagnostics: Diagnostic[];
  setDiagnostics: (uri: string, items: Omit<Diagnostic, 'uri'>[]) => void;
  clearUri: (uri: string) => void;
  clearAll: () => void;
}

export const useProblemsStore = create<ProblemsState>((set) => ({
  diagnostics: [],

  // setDiagnostics 以 URI 为键整体替换（对应 textDocument/publishDiagnostics 语义）。
  setDiagnostics: (uri, items) =>
    set((s) => ({
      diagnostics: [...s.diagnostics.filter((d) => d.uri !== uri), ...items.map((d) => ({ ...d, uri }))],
    })),

  clearUri: (uri) =>
    set((s) => ({ diagnostics: s.diagnostics.filter((d) => d.uri !== uri) })),

  clearAll: () => set({ diagnostics: [] }),
}));

// applyPublishDiagnostics 规范化 LSP publishDiagnostics 通知参数并入 Problems 数据。
export function applyPublishDiagnostics(params: unknown) {
  const p = params as { uri?: string; diagnostics?: Array<Omit<Diagnostic, 'uri'>> };
  if (!p?.uri) return;
  useProblemsStore.getState().setDiagnostics(p.uri, p.diagnostics ?? []);
}

export function severityLabel(severity: number): string {
  switch (severity) {
    case 2:
      return 'Warning';
    case 3:
      return 'Information';
    case 4:
      return 'Hint';
    case 1:
    default:
      return 'Error';
  }
}