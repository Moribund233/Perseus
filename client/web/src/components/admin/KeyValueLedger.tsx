import type { ReactNode } from 'react';

export interface LedgerRow {
  key: string;
  label: string;
  value: ReactNode;
}

interface KeyValueLedgerProps {
  rows: LedgerRow[];
}

export default function KeyValueLedger({ rows }: KeyValueLedgerProps) {
  return (
    <div className="ac-ledger">
      {rows.map((row) => (
        <div className="ac-ledger-row" key={row.key}>
          <span className="ac-ledger-key">{row.label}</span>
          <span className="ac-ledger-val">{row.value}</span>
        </div>
      ))}
    </div>
  );
}