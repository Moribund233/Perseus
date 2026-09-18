import type { CSSProperties } from 'react';

export type LogoVariant = 'color' | 'reverse' | 'mono';

interface LogoProps {
  size?: number | string;
  variant?: LogoVariant;
  noGap?: boolean;
  className?: string;
  style?: CSSProperties;
  title?: string;
}

const BODY_FILL: Record<LogoVariant, string> = {
  color: '#2649E0',
  reverse: '#FFFFFF',
  mono: 'currentColor',
};

const HEAD_FILL: Record<LogoVariant, string> = {
  color: '#101C3D',
  reverse: '#A8C2FF',
  mono: 'currentColor',
};

export default function Logo({
  size = 20,
  variant = 'reverse',
  noGap = false,
  className,
  style,
  title = 'Perseus',
}: LogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={className}
      style={style}
      role="img"
      aria-label={title}
      focusable="false"
    >
      <g fill={BODY_FILL[variant]}>
        <g opacity={0.4}>
          <path d="M58 21 L50.4 30.4 L48.6 28.6 Z" />
          <circle cx="49.5" cy="29.5" r="1.9" />
        </g>
        <g opacity={0.55}>
          <path d="M53.5 33.5 Q44 42 36.4 53.4 L33.6 50.6 Q45 40.5 53.5 33.5 Z" />
          <circle cx="35" cy="52" r="2.6" />
        </g>
        <path d="M50.5 11.5 Q32 27.5 22.7 45 L18.5 41 Q34.5 23.5 50.5 11.5 Z" />
        <circle cx="11.5" cy="14.5" r="1.6" opacity={0.9} />
        <circle cx="29" cy="7.5" r="1.15" opacity={0.5} />
        <circle cx="56.5" cy="53.5" r="1.35" opacity={0.65} />
        <circle cx="7.5" cy="35" r="1" opacity={0.35} />
        {noGap && <path d="M22.7 45 L18.5 41 L16.2 47.6 Z" />}
      </g>
      <circle cx="16.2" cy="47.6" r="4.6" fill={HEAD_FILL[variant]} />
    </svg>
  );
}
