import { badgeFor } from '../format';
import type { RankedVariable } from '../dataClient';
import { Icon, type IconName } from './Icon';

const ICONS: Record<string, IconName> = { 'badge--sig': 'significant', 'badge--nosig': 'not-significant', 'badge--none': 'no-data' };

/** Significance badge: the status icon is decorative, the word next to it carries the meaning. */
export function StatusBadge({ r, large = false }: { r: Pick<RankedVariable, 'tier' | 'significant'>; large?: boolean }) {
  const badge = badgeFor(r);
  return (
    <span className={`badge ${badge.cls}${large ? ' badge--lg' : ''}`}>
      <Icon name={ICONS[badge.cls]} size={large ? 18 : 13} />
      {badge.text}
    </span>
  );
}
