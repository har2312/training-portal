import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { Card, Table } from "../shared/ui";

// Admin directory of all personnel. Includes Performance Score (admin view).
export default function PersonnelDirectory() {
  const [people, setPeople] = useState([]);
  useEffect(() => { api.getPersonnelDirectory().then(setPeople).catch(console.error); }, []);

  return (
    <Card title="Personnel Directory">
      <Table columns={["ID", "Name", "Designation", "Stream", "Zone", "Station", "Svc. Left", "Trainings", "Perf."]}>
        {people.map((p) => (
          <tr key={p.personnel_id} className="hover:bg-slate-50">
            <td className="py-2 pr-4 font-mono text-xs">{p.personnel_id}</td>
            <td className="py-2 pr-4">{p.name}</td>
            <td className="py-2 pr-4">{p.designation}</td>
            <td className="py-2 pr-4">{p.stream}</td>
            <td className="py-2 pr-4">{p.zone}</td>
            <td className="py-2 pr-4">{p.station}</td>
            <td className="py-2 pr-4">{p.service_time_left} yr</td>
            <td className="py-2 pr-4">{p.trainings_completed}</td>
            <td className="py-2 pr-4 font-semibold text-blue-900">{p.performance_score}</td>
          </tr>
        ))}
      </Table>
    </Card>
  );
}
