import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { Card, Button } from "../shared/ui";

const EMPTY = {
  program_id: "", title: "", domain: "Engineering", topic: "AI",
  allowedDesignations: [], from_date: "", to_date: "",
  duration_days: 5, venue: "", capacity: 20, target_zone: "All",
};

export default function WorkshopForm({ onCreated }) {
  const [form, setForm] = useState(EMPTY);
  const [meta, setMeta] = useState({ topics: [], designations: [] });
  const [titles, setTitles] = useState([]);
  const [showTitles, setShowTitles] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    api.getMeta().then(setMeta).catch(console.error);
    api.getWorkshopTitles().then(setTitles).catch(console.error);
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  // ---- designation multi-select ----
  const addGrade = (g) => {
    if (g && !form.allowedDesignations.includes(g)) {
      setForm({ ...form, allowedDesignations: [...form.allowedDesignations, g] });
    }
  };
  const removeGrade = (g) =>
    setForm({ ...form, allowedDesignations: form.allowedDesignations.filter((d) => d !== g) });

  // ---- title autocomplete ----
  const titleMatches = form.title.trim()
    ? titles.filter((t) => t.toLowerCase().includes(form.title.toLowerCase()) && t !== form.title)
    : titles;

  async function submit(e) {
    e.preventDefault();
    setMsg(null);
    if (form.allowedDesignations.length === 0) {
      setMsg({ ok: false, text: "Select at least one eligible designation." });
      return;
    }
    try {
      await api.createWorkshop({
        program_id: form.program_id,
        title: form.title,
        domain: form.domain,
        topic: form.topic,
        allowed_designations: form.allowedDesignations,
        level_of_participants: form.allowedDesignations.join("/"),
        from_date: form.from_date,
        to_date: form.to_date,
        duration_days: Number(form.duration_days),
        venue: form.venue,
        capacity: Number(form.capacity),
        target_zone: form.target_zone,
      });
      setMsg({ ok: true, text: `Workshop ${form.program_id} created.` });
      setForm(EMPTY);
      api.getWorkshopTitles().then(setTitles).catch(console.error);
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

        {/* Title with autocomplete */}
        <div className="relative">
          <input
            className={field}
            placeholder="Title (type to search past titles)"
            value={form.title}
            onChange={(e) => { setForm({ ...form, title: e.target.value }); setShowTitles(true); }}
            onFocus={() => setShowTitles(true)}
            onBlur={() => setTimeout(() => setShowTitles(false), 120)}
            autoComplete="off"
            required
          />
          {showTitles && titleMatches.length > 0 && (
            <ul className="absolute z-20 mt-1 w-full max-h-44 overflow-y-auto bg-white border border-slate-200 rounded-md shadow-lg">
              {titleMatches.slice(0, 8).map((t) => (
                <li key={t}>
                  <button
                    type="button"
                    onMouseDown={() => { setForm({ ...form, title: t }); setShowTitles(false); }}
                    className="w-full text-left px-3 py-1.5 text-sm text-slate-700 hover:bg-blue-50"
                  >
                    {t}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <span className={label}>Topic</span>
          <select className={field} value={form.topic} onChange={set("topic")}>
            {meta.topics.map((t) => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <span className={label}>Stream (legacy tag)</span>
          <select className={field} value={form.domain} onChange={set("domain")}>
            <option>Engineering</option><option>Programme</option><option>Administration</option>
          </select>
        </div>

        {/* Eligible designations — pick any set, not a threshold */}
        <div className="col-span-2">
          <span className={label}>Eligible Designations (select one or more)</span>
          <select
            className={field}
            value=""
            onChange={(e) => { addGrade(e.target.value); e.target.value = ""; }}
          >
            <option value="" disabled>+ Add a designation…</option>
            {meta.designations
              .filter((d) => !form.allowedDesignations.includes(d))
              .map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <div className="flex flex-wrap gap-2 mt-2 min-h-[1.75rem]">
            {form.allowedDesignations.length === 0 && (
              <span className="text-xs text-slate-400">No designations selected yet.</span>
            )}
            {form.allowedDesignations.map((d) => (
              <span key={d} className="inline-flex items-center gap-1 bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded-full">
                {d}
                <button
                  type="button"
                  onClick={() => removeGrade(d)}
                  className="text-blue-500 hover:text-blue-900 leading-none"
                  aria-label={`Remove ${d}`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>

        <div>
          <span className={label}>Target Zone</span>
          <select className={field} value={form.target_zone} onChange={set("target_zone")}>
            <option>All</option><option>North</option><option>South</option><option>East</option>
            <option>West</option><option>North-East</option><option>Central</option>
          </select>
        </div>
        <div><span className={label}>Venue</span><input className={field} placeholder="Venue" value={form.venue} onChange={set("venue")} /></div>

        <div><span className={label}>From</span><input className={field} type="date" value={form.from_date} onChange={set("from_date")} /></div>
        <div><span className={label}>To</span><input className={field} type="date" value={form.to_date} onChange={set("to_date")} /></div>
        <div><span className={label}>Duration (days)</span><input className={field} type="number" value={form.duration_days} onChange={set("duration_days")} /></div>
        <div><span className={label}>Capacity</span><input className={field} type="number" value={form.capacity} onChange={set("capacity")} /></div>

        <div className="col-span-2 flex items-center gap-3">
          <Button type="submit">Create Workshop</Button>
          {msg && <span className={`text-sm ${msg.ok ? "text-emerald-700" : "text-red-700"}`}>{msg.text}</span>}
        </div>
      </form>
    </Card>
  );
}
