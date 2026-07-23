import { useEffect, useState } from "react";
import { api } from "../../api/client";

// Top KPI row: Total Workshops, Personnel Trained, AI Confidence.
// `refreshKey` lets the parent force a refetch after allot/retrain actions.
function Metric({ label, value, sub, accent }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-sm p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-3xl font-semibold ${accent}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
    </div>
  );
}

export default function MetricCards({ refreshKey }) {
  const [m, setM] = useState(null);
  useEffect(() => { api.getMetrics().then(setM).catch(console.error); }, [refreshKey]);

  const conf = m ? Math.round(m.ai_confidence * 100) : 0;
  return (
    <div className="grid grid-cols-3 gap-4">
      <Metric label="Total Workshops" value={m?.total_workshops ?? "—"} accent="text-blue-900" />
      <Metric label="Personnel Trained" value={m?.personnel_trained ?? "—"} sub="Accepted allotments" accent="text-emerald-700" />
      <Metric label="AI Confidence" value={m ? `${conf}%` : "—"} sub="Model accuracy on feedback" accent="text-slate-800" />
    </div>
  );
}
