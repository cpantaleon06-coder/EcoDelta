import { loadRegionDetail, type Region, type Variable } from '../dataClient';
import { useAsync } from '../useAsync';
import { fmtSigned } from '../format';
import { varIcon } from '../viz';
import { NOT_CAUSAL, signalsTogether } from '../results';
import { ErrorBox, Loading } from './Status';
import { Icon } from './Icon';
import { Direction } from './RankingPanel';
import { AreaTag, Coverage, Evidence } from './ResultMeta';

/** Earth system profile: one row per variable in this build for the selected region, plus what changed together. */
export function Profile({ region, variables }: { region: Region; variables: Variable[] }) {
  const { data, error } = useAsync(() => loadRegionDetail(region.id), [region.id]);
  if (error) return <ErrorBox error={error} />;
  if (!data || data.region.id !== region.id) return <Loading label="Loading profile…" minHeight={240} />;
  const rows = variables.flatMap((variable) => (data.variables[variable.id] ? [{ variable, v: data.variables[variable.id] }] : []));
  return (
    <section className="profile" aria-labelledby="profile-title">
      <h2 id="profile-title">
        <Icon name="globe" size={22} className="title-icon" />
        Earth system profile: {region.name} <AreaTag region={region} />
      </h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Variable</th>
              <th scope="col">Direction</th>
              <th scope="col">Magnitude per decade (95% CI)</th>
              <th scope="col">Evidence</th>
              <th scope="col">Coverage</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ variable, v }) => {
              const hm = v.answers.how_much;
              return (
                <tr key={variable.id}>
                  <th scope="row">
                    {varIcon(variable.id) && <Icon name={varIcon(variable.id)!} size={18} className="title-icon" />}
                    {variable.name}
                  </th>
                  <td>
                    <Direction r={{ significant: v.score.significant, verdict: v.answers.what.verdict, tier: v.score.tier }} />
                  </td>
                  <td className="num">
                    {hm.slope_per_decade === null || !hm.ci_per_decade
                      ? 'not available'
                      : `${fmtSigned(hm.slope_per_decade)} ${variable.public_unit} (${fmtSigned(hm.ci_per_decade[0])} to ${fmtSigned(hm.ci_per_decade[1])})`}
                  </td>
                  <td>
                    <Evidence cls={v.evidence?.class} capped={v.evidence?.capped_by_coverage} />
                  </td>
                  <td>
                    <Coverage where={v.answers.where} compact />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="profile__signals">
        {signalsTogether(rows.map(({ variable, v }) => ({ name: variable.name, evidence: v.evidence?.class, direction: v.answers.what.direction })))}{' '}
        <strong>{NOT_CAUSAL}</strong>
      </p>
    </section>
  );
}
