import { useState } from "react";
import { api } from "../api/client";
import { Button } from "../components/shared/ui";

// Login gate. On success, lifts the authenticated user up to App, which then
// renders the Admin or Personnel dashboard based on role.
export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState(null);

  async function submit(e) {
    e.preventDefault();
    setErr(null);
    try {
      const user = await api.login(username, password);
      onLogin(user);
    } catch (e) {
      setErr(e.message);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100">
      <form onSubmit={submit} className="bg-white border border-slate-200 rounded-lg shadow-sm p-8 w-96 space-y-4">
        <div className="text-center">
          <h1 className="text-lg font-semibold text-blue-900">Smart Training Allotment</h1>
          <p className="text-xs text-slate-500 mt-1">Prasar Bharati · NABM</p>
        </div>
        <input
          className="border border-slate-300 rounded-md px-3 py-2 text-sm w-full"
          placeholder="Username (admin / pb001)"
          value={username} onChange={(e) => setUsername(e.target.value)} required
        />
        <input
          type="password"
          className="border border-slate-300 rounded-md px-3 py-2 text-sm w-full"
          placeholder="Password"
          value={password} onChange={(e) => setPassword(e.target.value)} required
        />
        {err && <p className="text-sm text-red-700">{err}</p>}
        <Button type="submit" className="w-full justify-center">Sign In</Button>
      </form>
    </div>
  );
}
