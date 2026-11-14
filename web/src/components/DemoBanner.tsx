import { isDemoData, loadMeta } from '../dataClient';
import { useAsync } from '../useAsync';

export function DemoBanner() {
  const { data: meta, error } = useAsync(loadMeta, []);
  if (error) return null; // the page itself shows the load error
  if (!meta || !isDemoData(meta)) return null;
  return (
    <div className="demo-banner" role="note">
      <strong>DEMO DATA</strong>
      <span>These numbers come from a synthetic test set, not from real observations. Do not use them.</span>
    </div>
  );
}
