import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { TopicBadge } from "../shared/ui";

// "The Oracle" — AI predictive skill-gap recommendations (K-Means clustering).
// Sits at the top of the admin dashboard as a hero insight strip.
export default function OracleWidget() {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getOracle().then(setInsights).catch(console.error).finally(() => setLoading(false));
  }, []);

  return (
    <section className="rounded-lg border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white shadow-sm">
      <header className="flex items-center gap-2 px-5 py-3 border-b border-indigo-100">
        <span className="text-lg" aria-hidden>🔮</span>
        <h2 className="text-sm font-semibold tracking-wide text-indigo-900 uppercase">
          The Oracle — Predictive Skill-Gap Analysis
        </h2>
        <span className="ml-auto text-xs text-indigo-400">Unsupervised · K-Means</span>
      </header>
      <div className="p-5 space-y-3">
        {loading && <p className="text-sm text-slate-500">Analyzing the personnel base…</p>}
        {!loading && insights.length === 0 && (
          <p className="text-sm text-slate-500">No significant skill gaps detected.</p>
        )}
        {insights.map((it) => (
          <div key={it.cluster} className="flex items-start gap-3 rounded-md bg-white border border-slate-100 p-3">
            <TopicBadge topic={it.weak_topic} />
            <div className="flex-1">
              <p className="text-sm text-slate-700">{it.recommendation}</p>
              <p className="mt-1 text-xs text-slate-400">
                {it.count} personnel · {it.designation} · {it.zone} · avg {it.avg_years_since_training} yrs since training
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
