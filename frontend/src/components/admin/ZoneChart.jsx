import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { api } from "../../api/client";
import { Card } from "../shared/ui";

// Training Distribution by Zone — bar chart of accepted allotments per zone.
const COLORS = ["#1e3a8a", "#047857", "#b45309", "#7c3aed", "#0e7490"];

export default function ZoneChart({ refreshKey }) {
  const [data, setData] = useState([]);
  useEffect(() => {
    api.getMetrics().then((m) => setData(m.zone_distribution)).catch(console.error);
  }, [refreshKey]);

  return (
    <Card title="Training Distribution by Zone">
      {data.length === 0 ? (
        <p className="text-sm text-slate-500 py-8 text-center">
          No accepted allotments yet — run Auto-Allot and accept candidates to populate.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: -16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="zone" tick={{ fontSize: 12, fill: "#475569" }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#475569" }} />
            <Tooltip cursor={{ fill: "#f1f5f9" }} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
