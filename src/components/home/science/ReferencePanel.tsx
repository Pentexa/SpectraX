"use client";

import { useCallback, useState } from "react";
import { useScienceRequest } from "@/hooks/useScienceRequest";
import { scienceApi } from "@/lib/api/science";
import { controlClass, Panel, Status } from "./Panel";
import { SciencePlot } from "./SciencePlot";

export function ReferencePanel({ targetId }: { targetId: string }) {
  const [requested, setRequested] = useState(0);
  const load = useCallback((signal: AbortSignal) => scienceApi.reference(targetId, signal), [targetId]);
  const curve = useScienceRequest(requested ? load : null, requested);
  const points = curve.data?.points.filter((point) => !point.fainter_than) ?? [];
  return (
    <Panel title="Optical reference" actions={<button type="button" className={controlClass}
      disabled={curve.loading} onClick={() => setRequested((value) => value + 1)}>Load light curve</button>}>
      {!requested && <Status>Independent AAVSO optical observations.</Status>}
      {curve.loading && <Status>Loading AAVSO photometry…</Status>}
      {curve.error && <Status error>{curve.error}</Status>}
      {curve.data && (
        <>
          <Status>{curve.data.source} · {curve.data.band} · apparent magnitude</Status>
          {points.length > 0 ? <SciencePlot magnitude points={points.map((point) => ({ x: point.mjd, y: point.magnitude }))}
            xLabel="MJD" label="AAVSO optical magnitude over time" /> : <Status>No optical measurements in this interval.</Status>}
          <p className="text-[10px] text-text-muted">{curve.data.acknowledgment}</p>
        </>
      )}
    </Panel>
  );
}
