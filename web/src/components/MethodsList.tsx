import { describeValue, humanizeKey } from '../format';

/** meta.methods as a definition list, exactly as exported. */
export function MethodsList({ methods }: { methods: Record<string, unknown> }) {
  return (
    <dl className="methods">
      {Object.entries(methods).map(([k, v]) => (
        <div key={k}>
          <dt>{humanizeKey(k)}</dt>
          <dd>{describeValue(v)}</dd>
        </div>
      ))}
    </dl>
  );
}
