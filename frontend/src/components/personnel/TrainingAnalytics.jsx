import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { api } from "../../api/client";
import { Card } from "../shared/ui";

// Visual analytics for the employee: total trainings + topic-wise breakdown.
const COLORS = {
  AI: "#7c3aed", Signal: "#0284c7", Content: "#059669",
  Administration: "#b45309", Awareness: "#e11d48",
};

export default function TrainingAnalytics({ personnelId }) {
  const [data, setData] = useState(null);
  useEffect(() => { api.getMyAnalytics(personnelId).then(setData).catch(console.error); }, [personnelId]);

  if (!data) return <Card title="My Training Analytics"><p className="text-sm text-slate-500">Loading…</p></Card>;

  const pie = data.topic_breakdown.map((t) => ({ name: t.topic, value: t.count }));

  return (
    <Card title="My Training Analytics">
      <div className="grid grid-cols-2 gap-6 items-center">
        <div className="text-center">
          <p className="text-5xl font-semibold text-blue-900">{data.total_trainings}</p>
          <p className="text-xs uppercase tracking-wide text-slate-500 mt-1">Total Trainings Completed</p>
          <div className="mt-4 space-y-1 text-left">
            {data.topic_breakdown.map((t) => (
              <div key={t.topic} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS[t.topic] || "#94a3b8" }} />
                  {t.topic}
                </span>
                <span className="font-medium text-slate-700">{t.count}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          {pie.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-10">No trainings recorded yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pie} dataKey="value" nameKey="name" innerRadius={45} outerRadius={80} paddingAngle={2}>
                  {pie.map((e) => <Cell key={e.name} fill={COLORS[e.name] || "#94a3b8"} />)}
                </Pie>
                <Tooltip />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </Card>
  );
}
