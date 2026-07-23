import { useState } from "react";
import toast from "react-hot-toast";
import { api } from "../../api/client";

// Triggers /api/ai/retrain with a loading state and a success toast.
// Calls onRetrained() so the dashboard can refresh its confidence metric.
export default function RetrainButton({ onRetrained }) {
  const [loading, setLoading] = useState(false);

  async function retrain() {
    setLoading(true);
    try {
      const r = await api.retrain();
      toast.success(
        `AI retrained on ${r.samples} samples · confidence ${Math.round(r.confidence * 100)}%`
      );
      onRetrained?.();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={retrain}
      disabled={loading}
      className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold
                 text-white bg-blue-900 hover:bg-blue-800 disabled:opacity-60 shadow-sm transition"
    >
      <span className={loading ? "animate-spin" : ""} aria-hidden>
        {loading ? "↻" : "⚙"}
      </span>
      {loading ? "Retraining…" : "Retrain AI Model"}
    </button>
  );
}
