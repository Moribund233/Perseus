import type { ReactNode } from 'react';
import type { Tone } from './health';

interface HealthChipProps {
  tone: Tone;
  children: ReactNode;
}

export default function HealthChip({ tone, children }: HealthChipProps) {
  return <span className={`ac-chip ${tone}`}>{children}</span>;
}