import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { Card, Button } from "../shared/ui";

const EMPTY = {
  program_id: "", title: "", domain: "Engineering", topic: "AI",
  min_designation: "AD", level_of_participants: "", from_date: "", to_date: "",
  duration_days: 5, venue: "", capacity: 20, target_zone: "All",
};

export default function WorkshopForm({ onCreated }) {
  const [form, setForm] = useState(EMPTY);
  const [meta, setMeta] = useState({ topics: [], designations: [] });
  const [msg, setMsg] = useState(null);

  useEffect(() => { api.getMeta().then(setMeta).catch(console.error); }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setMsg(null);
    try {
      await api.createWorkshop({
        ...form,
        // keep a legacy label consistent with the new threshold
        level_of_participants: form.level_of_participants || `${form.min_designation} & above`,
        duration_days: Number(form.duration_days),
        capacity: Number(form.capacity),
      });
      setMsg({ ok: true, text: `Workshop ${form.program_id} created.` });
      setForm(EMPTY);
      onCreated?.();
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
  }

  const field = "border border-slate-300 rounded-md px-3 py-1.5 text-sm w-full";
  const label = "text-xs font-medium text-slate-500 mb-1 block";

  return (
    <Card title="Add Training Workshop">
      <form onSubmit={submit} className="grid grid-cols-2 gap-3">
        <input className={field} placeholder="Program ID (e.g. D26AI20)" value={form.program_id} onChange={set("program_id")} required />
        <input className={field} placeholder="Title" value={form.title} onChange={set("title")} required />

        <div>
          <span className={label}>Topic</span>
          <select className={field} value={form.topic} onChange={set("topic")}>
            {meta.topics.map((t) => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <span className={label}>Minimum Designation (&amp; above)</span>
          <select className={field} value={form.min_designation} onChange={set("min_designation")}>
            {meta.designations.map((d) => <option key={d}>{d}</option>)}
          </select>
        </div>

        <div>
          <span className={label}>Stream (legacy tag)</span>
          <select className={field} value={form.domain} onChange={set("domain")}>
            <option>Engineering</option><option>Programme</option><option>Administration</option>
          </select>
        </div>
        <div>
          <span className={label}>Target Zone</span>
          <select className={field} value={form.target_zone} onChange={set("target_zone")}>
            <option>All</option><option>North</option><option>South</option><option>East</option>
            <option>West</option><option>North-East</option><option>Central</option>
          </select>
        </div>

        <div><span className={label}>From</span><input className={field} type="date" value={form.from_date} onChange={set("from_date")} /></div>
        <div><span className={label}>To</span><input className={field} type="date" value={form.to_date} onChange={set("to_date")} /></div>
        <input className={field} type="number" placeholder="Duration (days)" value={form.duration_days} onChange={set("duration_days")} />
        <input className={field} placeholder="Venue" value={form.venue} onChange={set("venue")} />
        <input className={field} type="number" placeholder="Capacity" value={form.capacity} onChange={set("capacity")} />

        <div className="col-span-2 flex items-center gap-3">
          <Button type="submit">Create Workshop</Button>
          {msg && <span className={`text-sm ${msg.ok ? "text-emerald-700" : "text-red-700"}`}>{msg.text}</span>}
        </div>
      </form>
    </Card>
  );
}
