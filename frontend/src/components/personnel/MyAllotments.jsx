import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import toast from "react-hot-toast";
import { api } from "../../api/client";
import { Card, StatusBadge, TopicBadge } from "../shared/ui";

// "Action Required" — workshops the person is selected for. Accept confirms;
// Decline triggers the Smart Waitlist replacement on the backend (silently —
// no AI details are shown to personnel). Clean, non-intimidating layout.
export default function MyAllotments({ personnelId }) {
  const [items, setItems] = useState([]);

  const load = () => api.getMyAllotments(personnelId).then(setItems).catch(console.error);
  useEffect(() => {
    load();
    // Poll so invitations created by the admin appear without a manual reload.
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [personnelId]);

  async function decide(allotmentId, status) {
    try {
      const res = await api.updateAllotmentStatus(allotmentId, status);
      if (status === "Accepted") toast.success("You're confirmed for this workshop.");
      else toast(res.replacement_assigned
        ? "Declined. Your seat has been reassigned."
        : "Declined.", { icon: "✓" });
      load();
    } catch (e) { toast.error(e.message); }
  }

  const pending = items.filter((a) => a.status === "Pending");

  return (
    <Card title="Action Required">
      {pending.length === 0 && (
        <p className="text-sm text-slate-500">You have no pending training invitations. 🎉</p>
      )}
      <div className="space-y-3">
        <AnimatePresence initial={false}>
          {pending.map((a) => (
            <motion.div
              key={a.allotment_id}
              layout
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, x: -30 }}
              className="flex items-center justify-between border border-slate-200 rounded-lg p-4 bg-slate-50/50"
            >
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-medium text-slate-800">{a.title}</p>
                  <TopicBadge topic={a.topic} />
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  {a.venue} · {a.from_date} → {a.to_date} · {a.duration_days} days
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => decide(a.allotment_id, "Accepted")}
                  className="px-3 py-1.5 text-sm font-medium rounded-md bg-emerald-700 text-white hover:bg-emerald-600"
                >Accept</button>
                <button
                  onClick={() => decide(a.allotment_id, "Rejected")}
                  className="px-3 py-1.5 text-sm font-medium rounded-md bg-white border border-slate-300 text-slate-700 hover:bg-slate-100"
                >Decline</button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {items.some((a) => a.status !== "Pending") && (
        <div className="mt-6">
          <h3 className="text-xs uppercase tracking-wide text-slate-500 mb-2">Decided</h3>
          <div className="space-y-2">
            {items.filter((a) => a.status !== "Pending").map((a) => (
              <div key={a.allotment_id} className="flex items-center justify-between text-sm py-1">
                <span className="text-slate-700">{a.title}</span>
                <StatusBadge status={a.status} />
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
