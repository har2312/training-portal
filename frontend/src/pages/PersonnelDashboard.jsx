import { useState } from "react";
import { Toaster } from "react-hot-toast";
import MyProfile from "../components/personnel/MyProfile";
import MyAllotments from "../components/personnel/MyAllotments";
import MyTrainings from "../components/personnel/MyTrainings";
import TrainingAnalytics from "../components/personnel/TrainingAnalytics";
import ChatbotWidget from "../components/personnel/ChatbotWidget";

const TABS = ["Action Required", "My Trainings", "Analytics", "Profile"];

export default function PersonnelDashboard({ personnelId }) {
  const [tab, setTab] = useState("Action Required");

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
      <Toaster position="top-right" />
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

      {tab === "Action Required" && <MyAllotments personnelId={personnelId} />}
      {tab === "My Trainings" && <MyTrainings personnelId={personnelId} />}
      {tab === "Analytics" && <TrainingAnalytics personnelId={personnelId} />}
      {tab === "Profile" && <MyProfile personnelId={personnelId} />}

      <ChatbotWidget personnelId={personnelId} />
    </div>
  );
}
