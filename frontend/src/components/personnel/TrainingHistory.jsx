import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { Card, Table, StatusBadge } from "../shared/ui";

// Training history = the personnel's past/decided allotments (Accepted/Rejected).
export default function TrainingHistory({ personnelId }) {
  const [items, setItems] = useState([]);
  useEffect(() => {
    api.getMyAllotments(personnelId)
      .then((all) => setItems(all.filter((a) => a.status !== "Pending")))
      .catch(console.error);
  }, [personnelId]);

  return (
    <Card title="Training History">
      <Table columns={["Program", "Title", "Dates", "Status"]}>
        {items.map((a) => (
          <tr key={a.allotment_id} className="hover:bg-slate-50">
            <td className="py-2 pr-4 font-mono text-xs">{a.program_id}</td>
            <td className="py-2 pr-4">{a.title}</td>
            <td className="py-2 pr-4 text-xs text-slate-500">{a.from_date} → {a.to_date}</td>
            <td className="py-2 pr-4"><StatusBadge status={a.status} /></td>
          </tr>
        ))}
        {items.length === 0 && <tr><td colSpan={4} className="py-4 text-sm text-slate-500">No history yet.</td></tr>}
      </Table>
    </Card>
  );
}
