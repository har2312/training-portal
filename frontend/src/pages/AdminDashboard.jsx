import { useState } from "react";
import { Toaster } from "react-hot-toast";
import MetricCards from "../components/admin/MetricCards";
import ZoneChart from "../components/admin/ZoneChart";
import OracleWidget from "../components/admin/OracleWidget";
import RetrainButton from "../components/admin/RetrainButton";
import WorkshopForm from "../components/admin/WorkshopForm";
import WorkshopList from "../components/admin/WorkshopList";
import SmartAllotmentTable from "../components/admin/SmartAllotmentTable";
import PersonnelDirectory from "../components/admin/PersonnelDirectory";

const TABS = ["Command Center", "Workshops", "Directory"];

export default function AdminDashboard() {
  const [tab, setTab] = useState("Command Center");
  const [refreshKey, setRefreshKey] = useState(0);   // bumps metrics/chart
  const [selected, setSelected] = useState(null);

  const bump = () => setRefreshKey((k) => k + 1);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
      <Toaster position="top-right" />

      <div className="flex items-center justify-between">
        <nav className="flex gap-2 border-b border-slate-200">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium -mb-px border-b-2 ${
                tab === t ? "border-blue-900 text-blue-900" : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
        <RetrainButton onRetrained={bump} />
      </div>

      {tab === "Command Center" && (
        <div className="space-y-6">
          <OracleWidget />
          <MetricCards refreshKey={refreshKey} />
          <ZoneChart refreshKey={refreshKey} />
          <WorkshopList refreshKey={refreshKey} onSelect={setSelected} />
          <SmartAllotmentTable programId={selected} />
        </div>
      )}

      {tab === "Workshops" && (
        <div className="space-y-6">
          <WorkshopForm onCreated={bump} />
          <WorkshopList refreshKey={refreshKey} onSelect={setSelected} />
          <SmartAllotmentTable programId={selected} />
        </div>
      )}

      {tab === "Directory" && <PersonnelDirectory />}
    </div>
  );
}
