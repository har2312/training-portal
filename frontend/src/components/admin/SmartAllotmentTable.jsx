import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import toast from "react-hot-toast";
import { api } from "../../api/client";
import { Card, StatusBadge } from "../shared/ui";
import SearchAddPersonnel from "./SearchAddPersonnel";

// Match Score progress bar (0-100%), colored by strength.
function MatchBar({ value }) {
  const pct = Math.round((value ?? 0) * 100);
  const color = pct >= 75 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-slate-400";
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 h-2 rounded-full bg-slate-200 overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-slate-600 w-9 text-right">{pct}%</span>
    </div>
  );
}

// AI Insights tooltip: hover the badge to see the Explainable-AI reason.
function AiInsight({ reason }) {
  return (
    <span className="relative group inline-flex">
      <span className="cursor-help text-xs font-semibold text-blue-800 bg-blue-50 border border-blue-200 rounded px-1.5 py-0.5">
        AI ⓘ
      </span>
      <span className="pointer-events-none absolute z-10 left-1/2 -translate-x-1/2 bottom-full mb-2 w-64
                       opacity-0 group-hover:opacity-100 transition bg-slate-900 text-white text-xs
                       rounded-md px-3 py-2 shadow-lg">
        <span className="block font-semibold text-blue-200 mb-1">Why the AI chose them</span>
        {reason || "No explanation available."}
      </span>
    </span>
  );
}

export default function SmartAllotmentTable({ programId }) {
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(null);

  const load = () => {
    if (!programId) { setRows([]); return; }
    api.getAdminAllotments(programId).then(setRows).catch(console.error);
  };

  useEffect(() => {
    load();
    if (!programId) return;
    // Poll so personnel Accept/Decline actions (and auto-replacements) surface
    // here. Skip refetch while an admin action is mid-flight to avoid flicker.
    const t = setInterval(() => { if (!busy) load(); }, 5000);
    return () => clearInterval(t);
  }, [programId, busy]);

  async function accept(id) {
    setBusy(id);
    try {
      const updated = await api.acceptAllotment(id);
      setRows((rs) => rs.map((r) => (r.allotment_id === id ? updated : r)));
      toast.success("Allotment accepted");
    } catch (e) { toast.error(e.message); } finally { setBusy(null); }
  }

  async function reject(id) {
    setBusy(id);
    try {
      const { replacement } = await api.rejectAllotment(id);
      // Slide the rejected row out, then slide the replacement in.
      setRows((rs) => rs.filter((r) => r.allotment_id !== id));
      if (replacement) {
        setRows((rs) => [...rs, replacement]);
        toast.success(`Replaced with ${replacement.name}`);
      } else {
        toast("Rejected — no eligible replacement left", { icon: "⚠️" });
      }
    } catch (e) { toast.error(e.message); } finally { setBusy(null); }
  }

  if (!programId) {
    return <Card title="Smart Allotment"><p className="text-sm text-slate-500">Select a workshop above to view AI recommendations.</p></Card>;
  }

  return (
    <Card
      title={`Smart Allotment — ${programId}`}
      action={
        <button onClick={load} className="text-xs font-medium text-blue-800 hover:text-blue-600">
          ↻ Refresh
        </button>
      }
    >
      <SearchAddPersonnel programId={programId} onAdded={load} />
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead>
            <tr className="text-xs uppercase tracking-wide text-slate-500 border-b border-slate-200">
              {["Personnel", "Zone", "Trainings", "Match Score", "Perf.", "Insight", "Status", "Actions"].map((c) => (
                <th key={c} className="py-2 pr-4 font-medium">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {rows.map((r) => (
                <motion.tr
                  key={r.allotment_id}
                  layout
                  initial={{ opacity: 0, x: 40 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -40 }}
                  transition={{ duration: 0.25 }}
                  className="border-b border-slate-100 hover:bg-slate-50"
                >
                  <td className="py-2 pr-4">
                    <div className="font-medium text-slate-800">{r.name}</div>
                    <div className="text-xs text-slate-400">{r.personnel_id} · {r.designation}</div>
                  </td>
                  <td className="py-2 pr-4">{r.zone}</td>
                  <td className="py-2 pr-4">{r.trainings_completed}</td>
                  <td className="py-2 pr-4"><MatchBar value={r.ml_match_probability} /></td>
                  <td className="py-2 pr-4 font-semibold text-blue-900">{r.performance_score}</td>
                  <td className="py-2 pr-4"><AiInsight reason={r.ai_reason} /></td>
                  <td className="py-2 pr-4"><StatusBadge status={r.status} /></td>
                  <td className="py-2 pr-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => accept(r.allotment_id)}
                        disabled={busy === r.allotment_id || r.status === "Accepted"}
                        className="px-2.5 py-1 text-xs font-medium rounded-md bg-emerald-700 text-white hover:bg-emerald-600 disabled:opacity-40"
                      >Accept</button>
                      <button
                        onClick={() => reject(r.allotment_id)}
                        disabled={busy === r.allotment_id}
                        className="px-2.5 py-1 text-xs font-medium rounded-md bg-red-700 text-white hover:bg-red-600 disabled:opacity-40"
                      >Reject</button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
            {rows.length === 0 && (
              <tr><td colSpan={8} className="py-4 text-sm text-slate-500">No allotments yet. Run Auto-Allot on the workshop.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
