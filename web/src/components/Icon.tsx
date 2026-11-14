import type { ReactNode } from 'react';

// Custom icon set (drawn for EcoDelta, no third-party paths) in a flat technical-label style: solid shapes
// mixed with 1.5px hairlines on a 24px grid, crosshairs, sparkles, block arrows, wireframe globes, hatching
// and seals with a cut-out symbol. One color: everything is currentColor, which the CSS sets to green.
const F = { fill: 'currentColor', stroke: 'none' };
const THICK = { strokeWidth: 2.5 };
const CHECK = 'M7.5 12.5l1.8-1.8 1.7 1.7 3.9-3.9 1.8 1.8-5.7 5.7z';
const DISC = 'M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18z';

// a 12-point sawtooth seal, the shape of a certification stamp
const SEAL = (() => {
  const pts = Array.from({ length: 24 }, (_, i) => {
    const a = (i * Math.PI) / 12 - Math.PI / 2;
    const r = i % 2 ? 8.2 : 10;
    return `${(12 + r * Math.cos(a)).toFixed(2)} ${(12 + r * Math.sin(a)).toFixed(2)}`;
  });
  return `M${pts.join('L')}z`;
})();

const PATHS = {
  // variables
  temperature: (
    <>
      <path d="M10 14V5a2 2 0 0 1 4 0v9" />
      <circle cx="12" cy="17.5" r="4.5" style={F} />
      <path d="M11.25 8h1.5v6h-1.5z" style={F} />
      <path d="M16 6h3M16 9h2M16 12h3" />
      <path d="M5.5 2.5l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z" style={F} />
    </>
  ),
  precipitation: (
    <>
      <path d="M7 15a4 4 0 0 1 .5-8 5.5 5.5 0 0 1 10.3 1.5A3.3 3.3 0 0 1 17.5 15z" style={F} />
      <path d="M8 17.5l-2 4M12.5 17.5l-2 4M17 17.5l-2 4" style={THICK} />
    </>
  ),
  evaporation: (
    <>
      <path d="M6 11l6-6 6 6h-3.5L12 8.5 9.5 11zM6 16.5l6-6 6 6h-3.5L12 14l-2.5 2.5z" style={F} />
      <path d="M2 20.5c1.7-1.6 3.3-1.6 5 0s3.3 1.6 5 0 3.3-1.6 5 0 3.3 1.6 5 0" />
    </>
  ),
  runoff: (
    <>
      <path d="M2 9v13h13z" style={F} />
      <path d="M7 3l11 11" />
      <path d="M21 17h-6.5l6.5-6.5z" style={F} />
    </>
  ),
  soil: (
    <>
      <path d="M12 2l3.5 5.2a4.2 4.2 0 1 1-7 0z" style={F} />
      <path d="M3 14h18v2.5H3z" style={F} />
      {[4.5, 9.5, 14.5, 19.5].map((x) => (
        <circle key={x} cx={x} cy="19" r="1.1" style={F} />
      ))}
      <path d="M3 22h18" />
    </>
  ),
  // status
  significant: <path d={`${DISC}${CHECK}`} fillRule="evenodd" style={F} />,
  'not-significant': (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M7 10.75h10v2.5H7z" style={F} />
    </>
  ),
  increasing: <path d="M12 3l8 8h-5v10H9V11H4z" style={F} />,
  decreasing: <path d="M12 21l-8-8h5V3h6v10h5z" style={F} />,
  'no-data': (
    <>
      <circle cx="12" cy="12" r="9" strokeDasharray="1.5 2" />
      <path d="M5.5 18.5l13-13" style={THICK} />
    </>
  ),
  // interface
  // a folded map: three solid panels with gaps at the folds
  map: <path d="M2 6l5.5-2v14L2 20zM9.25 4l5.5 2v14l-5.5-2zM16.5 6L22 4v14l-5.5 2z" style={F} />,
  ranking: (
    <>
      {[6, 12, 18].map((y) => (
        <circle key={y} cx="4.5" cy={y} r="1.5" style={F} />
      ))}
      <path d="M8 4.75h13v2.5H8zM8 10.75h10v2.5H8zM8 16.75h7v2.5H8z" style={F} />
    </>
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <ellipse cx="12" cy="12" rx="4" ry="9" />
      <path d="M3 12h18M4.2 7.5h15.6M4.2 16.5h15.6" />
      <circle cx="12" cy="12" r="1.8" style={F} />
    </>
  ),
  info: <path d={`${DISC}M11 10.5h2V17h-2zM11 7h2v2h-2z`} fillRule="evenodd" style={F} />,
  download: <path d="M9 3h6v8h4l-7 7-7-7h4zM3 20h18v2.5H3z" style={F} />,
  external: (
    <>
      <path d="M3 9V3h6M3 15v6h6M15 21h6v-6" strokeWidth={2} />
      <path d="M9 15l9-9" style={THICK} />
      <path d="M21 3v8l-8-8z" style={F} />
    </>
  ),
  'arrow-right': <path d="M3 10h10V5l8 7-8 7v-5H3z" style={F} />,
  'arrow-left': <path d="M21 10H11V5l-8 7 8 7v-5h10z" style={F} />,
  // the four guided questions
  'q-what': (
    <path d="M12 2c.8 5.6 3.4 8.2 10 10-6.6 1.8-9.2 4.4-10 10-.8-5.6-3.4-8.2-10-10 6.6-1.8 9.2-4.4 10-10z" style={F} />
  ),
  'q-where': (
    <>
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" style={F} />
      <path d="M12 2v5M12 17v5M2 12h5M17 12h5" strokeWidth={2} />
    </>
  ),
  'q-how-much': <path d="M3 16h3v5H3zM8 12h3v9H8zM13 8h3v13h-3zM18 4h3v17h-3z" style={F} />,
  'q-trust': <path d={`${SEAL}${CHECK}`} fillRule="evenodd" style={F} />,
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
      strokeWidth={1.5}
      strokeLinecap="butt"
      strokeLinejoin="miter"
      focusable="false"
      {...a11y}
    >
      {PATHS[name]}
    </svg>
  );
}
