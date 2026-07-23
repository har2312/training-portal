import { useState } from "react";
import Login from "./pages/Login";
import AdminDashboard from "./pages/AdminDashboard";
import PersonnelDashboard from "./pages/PersonnelDashboard";

export default function App() {
  const [user, setUser] = useState(null);

  if (!user) return <Login onLogin={setUser} />;

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-blue-900 text-white">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-sm font-semibold">Smart Training Allotment System</h1>
            <p className="text-xs text-blue-200">Prasar Bharati · NABM</p>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span>{user.name} <span className="text-blue-300">({user.role})</span></span>
            <button onClick={() => setUser(null)} className="text-blue-200 hover:text-white">Sign out</button>
          </div>
        </div>
      </header>

      {user.role === "admin"
        ? <AdminDashboard />
        : <PersonnelDashboard personnelId={user.personnel_id} />}
    </div>
  );
}
