import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { api } from "../../api/client";
import { Card, Button, Table, TopicBadge, ScheduleBadge, PillTabs } from "../shared/ui";

// Workshops list with Topic filter + Upcoming/Ongoing/Completed sections and
// the Auto-Allot trigger.
const SCHEDULES = ["Upcoming", "Ongoing", "Completed"];

export default function WorkshopList({ refreshKey, onSelect }) {
  const [workshops, setWorkshops] = useState([]);
  const [topics, setTopics] = useState(["All"]);
  const [topic, setTopic] = useState("All");
  const [schedule, setSchedule] = useState("Upcoming");
  const [busy, setBusy] = useState(null);

  const load = () => api.getWorkshops().then(setWorkshops).catch(console.error);
  useEffect(() => { load(); }, [refreshKey]);
  useEffect(() => { api.getMeta().then((m) => setTopics(["All", ...m.topics])).catch(console.error); }, []);

  async function autoAllot(programId) {
    setBusy(programId);
    try {
      const res = await api.commitAllotment(programId);
      if (res.allotments_created > 0) {
        toast.success(`${res.allotments_created} personnel allotted — invitations sent`);
      } else {
        toast("Already fully allotted — no new invitations", { icon: "ℹ️" });
      }
      onSelect(programId);
    } catch (e) { toast.error(e.message); } finally { setBusy(null); }
  }

  const filtered = workshops.filter(
    (w) => (topic === "All" || w.topic === topic) && w.schedule_status === schedule
  );

  return (
    <Card
      title="Training Workshops"
      action={<PillTabs options={topics} value={topic} onChange={setTopic} />}
    >
      <div className="mb-3"><PillTabs options={SCHEDULES} value={schedule} onChange={setSchedule} /></div>
      <Table columns={["Program", "Title", "Topic", "Min. Desig.", "Zone", "Status", "Cap", "Actions"]}>
        {filtered.map((w) => (
          <tr key={w.program_id} className="hover:bg-slate-50">
            <td className="py-2 pr-4 font-mono text-xs">{w.program_id}</td>
            <td className="py-2 pr-4">{w.title}</td>
            <td className="py-2 pr-4"><TopicBadge topic={w.topic} /></td>
            <td className="py-2 pr-4 text-xs">{w.min_designation} +</td>
            <td className="py-2 pr-4">{w.target_zone}</td>
            <td className="py-2 pr-4"><ScheduleBadge status={w.schedule_status} /></td>
            <td className="py-2 pr-4">{w.capacity}</td>
            <td className="py-2 pr-4">
              <div className="flex gap-2">
                <Button onClick={() => autoAllot(w.program_id)} disabled={busy === w.program_id}>
                  {busy === w.program_id ? "Allotting…" : "Auto-Allot"}
                </Button>
                <Button variant="secondary" onClick={() => onSelect(w.program_id)}>View</Button>
              </div>
            </td>
          </tr>
        ))}
        {filtered.length === 0 && (
          <tr><td colSpan={8} className="py-4 text-sm text-slate-500">No {schedule.toLowerCase()} workshops{topic !== "All" ? ` in ${topic}` : ""}.</td></tr>
        )}
      </Table>
    </Card>
  );
}
