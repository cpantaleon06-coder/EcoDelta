import type { ComponentPropsWithoutRef, ElementType, ReactNode } from 'react';
import { sparkPoints, stripeColors, type YearValue } from '../viz';

type PanelProps<T extends ElementType> = { as?: T; children: ReactNode } & ComponentPropsWithoutRef<T>;

/** A card: surface tone and a faint neutral hairline. */
export function Panel<T extends ElementType = 'section'>({ as, className = '', children, ...rest }: PanelProps<T>) {
  const Tag = as ?? 'section';
  return (
    <Tag className={`panel ${className}`} {...rest}>
      {children}
    </Tag>
  );
}

/** One stripe per calendar year on the map palette. Decorative copy of data shown elsewhere in words. */
export function Stripes({ years, palette, className = '' }: { years: YearValue[]; palette: string[]; className?: string }) {
  if (years.length < 2) return null;
  const colors = stripeColors(
    years.map((y) => y.value),
    palette,
  );
  return (
    <div className={`stripes ${className}`} aria-hidden="true">
      {colors.map((c, i) => (
        <span key={years[i].year} style={{ background: c }} />
      ))}
    </div>
  );
}

/** Small line of the yearly values, in the variable's color. Decorative: the numbers are shown in text. */
export function Spark({ years }: { years: YearValue[] }) {
  if (years.length < 2) return null;
  return (
    <svg className="spark" viewBox="0 0 72 28" preserveAspectRatio="none" aria-hidden="true">
      <polyline
        pathLength={1}
        points={sparkPoints(
          years.map((y) => y.value),
          72,
          28,
        )}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
