import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { Card, Table, StatusBadge } from "../shared/ui";

// Admin-only roster: shows the allotted personnel INCLUDING the hidden
// Performance Score and each person's Accept/Reject status.
export default function AllotmentPanel({ programId }) {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    if (!programId) return;
    api.getAdminAllotments(programId).then(setRows).catch(console.error);
  }, [programId]);

  if (!programId) {
    return <Card title="Allotted Personnel"><p className="text-sm text-slate-500">Select a workshop to view its roster.</p></Card>;
  }

  return (
    <Card title={`Allotted Personnel — ${programId}`}>
      <Table columns={["ID", "Name", "Designation", "Zone", "Trainings", "ML Match", "Perf. Score", "Status"]}>
        {rows.map((r) => (
          <tr key={r.allotment_id} className="hover:bg-slate-50">
            <td className="py-2 pr-4 font-mono text-xs">{r.personnel_id}</td>
            <td className="py-2 pr-4">{r.name}</td>
            <td className="py-2 pr-4">{r.designation}</td>
            <td className="py-2 pr-4">{r.zone}</td>
            <td className="py-2 pr-4">{r.trainings_completed}</td>
            <td className="py-2 pr-4">{(r.ml_match_probability * 100).toFixed(1)}%</td>
            <td className="py-2 pr-4 font-semibold text-blue-900">{r.performance_score}</td>
            <td className="py-2 pr-4"><StatusBadge status={r.status} /></td>
          </tr>
        ))}
        {rows.length === 0 && (
          <tr><td colSpan={8} className="py-4 text-sm text-slate-500">No allotments yet. Run Auto-Allot.</td></tr>
        )}
      </Table>
    </Card>
  );
}
