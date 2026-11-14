import type { ReactNode } from 'react';

// Custom icon set (drawn for EcoDelta, no third-party paths). 24px grid, 2px stroke, square caps, miter joins,
// 45 degree chamfers instead of round corners. Two tones: the stroke is the neutral text color (currentColor)
// and one accent part follows --icon-accent, else the surrounding --var (variable color), else green.
const A = 'var(--icon-accent, var(--var, var(--green)))';
const fill = { fill: A, stroke: 'none' };
const line = { stroke: A };
const OCTAGON = 'M8 3h8l5 5v8l-5 5H8l-5-5V8z';

const PATHS = {
  // variables
  temperature: (
    <>
      <path d="M11 3h2l1 1v10l2 2v3l-2 2h-4l-2-2v-3l2-2V4z" />
      <path d="M11 9h2v6l1 1v2l-1 1h-2l-1-1v-2l1-1z" style={fill} />
      <path d="M17 6h2M17 10h2" />
    </>
  ),
  precipitation: (
    <>
      <path d="M6 15h12l2-2v-2l-2-2h-1l-1-2-2-2h-3l-2 2-1 3H6l-2 2v2z" />
      <path d="M8 18l-1 3M12 18l-1 3M16 18l-1 3" style={line} />
    </>
  ),
  evaporation: (
    <>
      <path d="M3 21l3-2 3 2 3-2 3 2 3-2 3 2" />
      <path d="M8 16V5M5 8l3-3 3 3M16 14V7M13 10l3-3 3 3" style={line} />
    </>
  ),
  runoff: (
    <>
      <path d="M3 9v12h12z" />
      <path d="M8 5l9 9M17 9v5h-5" style={line} />
      <path d="M17 21h4" />
    </>
  ),
  soil: (
    <>
      <path d="M3 15h18M3 18h18M3 21h18" />
      <path d="M12 3l4 5v2l-2 2h-4l-2-2V8z" style={fill} />
    </>
  ),
  // status
  significant: (
    <>
      <path d={OCTAGON} />
      <path d="M8 12l3 3 6-6" style={line} />
    </>
  ),
  'not-significant': (
    <>
      <path d={OCTAGON} />
      <path d="M8 12h8" style={line} />
    </>
  ),
  increasing: (
    <>
      <path d="M12 20V6M6 11l6-6 6 6" style={line} />
      <path d="M5 21h14" />
    </>
  ),
  decreasing: (
    <>
      <path d="M12 4v14M6 13l6 6 6-6" style={line} />
      <path d="M5 3h14" />
    </>
  ),
  'no-data': (
    <>
      <path d={OCTAGON} strokeDasharray="2 4" /* square caps add 1px to each end of a dash */ />
      <path d="M7 17L17 7" style={line} />
    </>
  ),
  // interface
  map: (
    <>
      <path d="M9 4l6 2v14l-6-2z" style={{ ...fill, opacity: 0.55 }} />
      <path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2zM9 4v14M15 6v14" />
    </>
  ),
  ranking: (
    <>
      <path d="M10 6h11M10 12h11M10 18h11" />
      <path d="M3 4h4v4H3zM3 10h4v4H3zM3 16h4v4H3z" style={fill} />
    </>
  ),
  globe: (
    <>
      <path d={OCTAGON} />
      <path d="M12 3l-3 4v10l3 4M12 3l3 4v10l-3 4" />
      <path d="M3 12h18" style={line} />
    </>
  ),
  info: (
    <>
      <path d={OCTAGON} />
      <path d="M12 11v6M12 7v1" style={line} />
    </>
  ),
  download: (
    <>
      <path d="M12 3v11M7 9l5 5 5-5" style={line} />
      <path d="M4 15v5h16v-5" />
    </>
  ),
  external: (
    <>
      <path d="M10 5H5v14h14v-5" />
      <path d="M14 4h6v6M20 4l-9 9" style={line} />
    </>
  ),
  'arrow-right': <path d="M4 12h15M13 6l6 6-6 6" />,
  'arrow-left': <path d="M20 12H5M11 6l-6 6 6 6" />,
  // the four guided questions
  'q-what': (
    <>
      <path d="M12 4l9 16H3z" />
      <path d="M12 10l4 7H8z" style={fill} />
    </>
  ),
  'q-where': (
    <>
      <path d="M12 21l-6-7V7l3-3h6l3 3v7z" />
      <path d="M10 8h4v4h-4z" style={fill} />
    </>
  ),
  'q-how-much': (
    <>
      <path d="M3 21h18M6 18v-4M11 18V10" />
      <path d="M15 6h4v12h-4z" style={fill} />
    </>
  ),
  'q-trust': (
    <>
      <path d="M12 3l8 3v7l-3 5-5 3-5-3-3-5V6z" />
      <path d="M8 12l3 3 5-5" style={line} />
    </>
  ),
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof PATHS;
export const ICON_NAMES = Object.keys(PATHS) as IconName[];

interface Props {
  name: IconName;
  size?: number;
  /** Accessible name. Give it only when the icon carries meaning that no text next to it says. */
  title?: string;
  /** Hidden from assistive technology. Defaults to true when there is no title. */
  decorative?: boolean;
  className?: string;
}

export function Icon({ name, size = 20, title, decorative = !title, className = '' }: Props) {
  const a11y = decorative ? { 'aria-hidden': true } : { role: 'img', 'aria-label': title };
  return (
    <svg
      className={`icon ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="square"
      strokeLinejoin="miter"
      focusable="false"
      {...a11y}
    >
      {PATHS[name]}
    </svg>
  );
}
