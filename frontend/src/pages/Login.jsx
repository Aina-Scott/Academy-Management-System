import { useState } from "react";
import { errMsg, login } from "../services/api";

export default function Login({ onLogin }) {
  const [f, setF] = useState({ username: "", password: "" });
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    // spinning
    if (loading) return;
    setLoading(true);
    setErr("");
    
    try { onLogin(await login(f.username, f.password)); }
    catch (x) { setErr(x.response?.status === 401 ? "Wrong username or password." : errMsg(x)); }
    finally { setLoading(false); }
  };

  return (
    <form className="login" onSubmit={submit} aria-busy={loading}>
      <h1>Academy Management System</h1>
      <input placeholder="Username" value={f.username} disabled={loading} onChange={(e) => setF({ ...f, username: e.target.value })} />
      <input type="password" placeholder="Password" value={f.password} disabled={loading} onChange={(e) => setF({ ...f, password: e.target.value })} />
      {err && <p className="err" role="alert">{err}</p>}
      <button className="btn login-submit" disabled={loading}>
        {loading && <span className="spinner" aria-hidden="true" />}
        {loading ? "Signing in..." : "Sign in"}
      </button>
      {loading && <span className="sr-only" role="status">Signing in</span>}
    </form>
  );
}
