import type { Tone } from './health';

interface StatusDotProps {
  tone: Tone;
  title?: string;
}

export default function StatusDot({ tone, title }: StatusDotProps) {
  return <span className={`ac-dot ${tone}`} title={title} aria-hidden="true" />;
}