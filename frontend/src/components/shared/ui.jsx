// Small shared UI primitives. Government-enterprise look: restrained palette
// (slate + a single navy accent), clear hierarchy, no flashy colors.

export function Card({ title, action, children }) {
  return (
    <section className="bg-white border border-slate-200 rounded-lg shadow-sm">
      {(title || action) && (
        <header className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
          <h2 className="text-sm font-semibold tracking-wide text-slate-700 uppercase">
            {title}
          </h2>
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Button({ variant = "primary", className = "", ...props }) {
  const styles = {
    primary: "bg-blue-900 text-white hover:bg-blue-800",
    secondary: "bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300",
    success: "bg-emerald-700 text-white hover:bg-emerald-600",
    danger: "bg-red-700 text-white hover:bg-red-600",
  }[variant];
  return (
    <button
      className={`px-3 py-1.5 text-sm font-medium rounded-md transition disabled:opacity-50 ${styles} ${className}`}
      {...props}
    />
  );
}

export function StatusBadge({ status }) {
  const map = {
    Pending: "bg-amber-100 text-amber-800",
    Accepted: "bg-emerald-100 text-emerald-800",
    Rejected: "bg-red-100 text-red-800",
    Completed: "bg-slate-200 text-slate-600",
  };
  return (
    <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${map[status] || "bg-slate-100 text-slate-700"}`}>
      {status}
    </span>
  );
}

const TOPIC_COLORS = {
  AI: "bg-violet-100 text-violet-800",
  Signal: "bg-sky-100 text-sky-800",
  Content: "bg-emerald-100 text-emerald-800",
  Administration: "bg-amber-100 text-amber-800",
  Awareness: "bg-rose-100 text-rose-800",
};

export function TopicBadge({ topic }) {
  if (!topic) return null;
  return (
    <span className={`px-2 py-0.5 text-xs font-semibold rounded ${TOPIC_COLORS[topic] || "bg-slate-100 text-slate-700"}`}>
      {topic}
    </span>
  );
}

export function ScheduleBadge({ status }) {
  const map = {
    Upcoming: "bg-blue-100 text-blue-800",
    Ongoing: "bg-emerald-100 text-emerald-800 animate-pulse",
    Completed: "bg-slate-200 text-slate-600",
  };
  return (
    <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${map[status] || "bg-slate-100"}`}>
      {status}
    </span>
  );
}

// Horizontal pill tabs, used for topic filters and schedule sections.
export function PillTabs({ options, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <button
          key={o}
          onClick={() => onChange(o)}
          className={`px-3 py-1 text-xs font-medium rounded-full border transition ${
            value === o
              ? "bg-blue-900 text-white border-blue-900"
              : "bg-white text-slate-600 border-slate-300 hover:bg-slate-50"
          }`}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

export function Table({ columns, children }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="text-xs uppercase tracking-wide text-slate-500 border-b border-slate-200">
            {columns.map((c) => (
              <th key={c} className="py-2 pr-4 font-medium">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  );
}
