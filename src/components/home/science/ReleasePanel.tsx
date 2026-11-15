import { useScienceRequest } from "@/hooks/useScienceRequest";
import { scienceApi } from "@/lib/api/science";
import { Panel, Status } from "./Panel";

export function ReleasePanel() {
  const { data, error, loading } = useScienceRequest(scienceApi.releases);
  return (
    <Panel title="SPHEREx releases">
      {loading && <Status>Loading the release catalog…</Status>}
      {error && <Status error>{error}</Status>}
      {data && <dl className="grid grid-cols-2 gap-1.5 font-mono text-[10px] leading-relaxed">
        {data.releases.map((release) => (
          <div key={release.id} className="rounded-[2px] border border-border-subtle px-2 py-1">
            <dt className="text-[#cad6e2]">{release.id}</dt>
            <dd className={release.status === "published" ? "text-cyan-bright" : "text-[#9caec0]"}>
              {release.status}{release.planned_month ? ` · ${release.planned_month}` : ""}
            </dd>
          </div>
        ))}
      </dl>}
    </Panel>
  );
}
