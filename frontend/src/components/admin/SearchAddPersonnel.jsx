import { useState } from "react";
import toast from "react-hot-toast";
import { api } from "../../api/client";

// Manual admin override: search a person by name/ID and append them to the
// workshop's allotment list after Auto-Allot has run.
export default function SearchAddPersonnel({ programId, onAdded }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [busy, setBusy] = useState(false);

  async function search(value) {
    setQ(value);
    if (value.trim().length < 2) { setResults([]); return; }
    try {
      setResults(await api.searchPersonnel(value.trim()));
    } catch (e) { console.error(e); }
  }

  async function add(pid, name) {
    setBusy(true);
    try {
      await api.manualAllot(programId, pid);
      toast.success(`${name} added to ${programId}`);
      setQ(""); setResults([]);
      onAdded?.();
    } catch (e) {
      toast.error(e.message);
    } finally { setBusy(false); }
  }

  if (!programId) return null;

  return (
    <div className="relative mb-4">
      <input
        value={q}
        onChange={(e) => search(e.target.value)}
        placeholder="🔍 Manually search & add a person by name or ID…"
        className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
      />
      {results.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full bg-white border border-slate-200 rounded-md shadow-lg max-h-56 overflow-y-auto">
          {results.map((p) => (
            <li key={p.personnel_id}
                className="flex items-center justify-between px-3 py-2 text-sm hover:bg-slate-50">
              <span>
                <span className="font-medium text-slate-800">{p.name}</span>
                <span className="text-xs text-slate-400 ml-2">{p.personnel_id} · {p.designation} · {p.zone}</span>
              </span>
              <button
                disabled={busy}
                onClick={() => add(p.personnel_id, p.name)}
                className="px-2.5 py-1 text-xs font-medium rounded-md bg-blue-900 text-white hover:bg-blue-800 disabled:opacity-50"
              >+ Add</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
