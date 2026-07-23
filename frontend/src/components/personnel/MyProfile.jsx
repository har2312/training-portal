import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { Card, TopicBadge } from "../shared/ui";

// Personnel self-profile + past training history. The API (PersonnelPublic /
// analytics) never sends performance_score or AI metadata, so there is nothing
// sensitive to hide on the client — defense is server-side.
export default function MyProfile({ personnelId }) {
  const [p, setP] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api.getProfile(personnelId).then(setP).catch(console.error);
    api.getMyAnalytics(personnelId).then((a) => setHistory(a.history)).catch(console.error);
  }, [personnelId]);

  if (!p) return <Card title="My Profile"><p className="text-sm text-slate-500">Loading…</p></Card>;

  const rows = [
    ["Personnel ID", p.personnel_id], ["Name", p.name],
    ["Designation", p.designation], ["Stream", p.stream],
    ["Specialization", p.specialization], ["Qualification", p.qualification],
    ["Zone", p.zone], ["Station", p.station], ["Age", p.age],
    ["Service Time Left", `${p.service_time_left} years`],
    ["Total Trainings", p.trainings_completed],
  ];

  return (
    <div className="space-y-6">
      <Card title="My Profile">
        <dl className="grid grid-cols-2 gap-y-3 gap-x-6">
          {rows.map(([label, val]) => (
            <div key={label} className="flex flex-col">
              <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
              <dd className="text-sm text-slate-800">{val ?? "—"}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card title="Training History">
        <div className="space-y-2">
          {history.map((h, i) => (
            <div key={i} className="flex items-center justify-between text-sm border-b border-slate-100 pb-2">
              <span className="flex items-center gap-2">
                <TopicBadge topic={h.topic} />
                <span className="text-slate-700">{h.title}</span>
              </span>
              <span className="text-xs text-slate-400">{h.completed_date}</span>
            </div>
          ))}
          {history.length === 0 && <p className="text-sm text-slate-500">No past trainings recorded.</p>}
        </div>
      </Card>
    </div>
  );
}
