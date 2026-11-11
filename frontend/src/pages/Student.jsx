import { useEffect, useState } from "react";
import api, { errMsg } from "../services/api";

const blank = {
  first_name: "", last_name: "", email: "", username: "", password: "",
  student_number: "", student_phone: "", staff_number: "", instructor_phone: "",
};

export default function Student({ role }) {
  const [list, setList] = useState([]);
  const [f, setF] = useState(blank);
  const [editing, setEditing] = useState(null);
  const [err, setErr] = useState("");

  const load = async () => setList((await api.get(`/users/?role=${role}`)).data);
  useEffect(() => { load().catch((e) => setErr(errMsg(e))); }, [role]);

  const reset = () => { setF(blank); setEditing(null); };
  const run = async (fn) => {
    try { setErr(""); await fn(); await load(); } catch (e) { setErr(errMsg(e)); }
  };
  const save = () => run(async () => {
    const { password, ...data } = f;
    if (password) data.password = password;
    if (editing) await api.patch(`/users/${editing}/`, data);
    else await api.post("/users/", { ...data, role });
    reset();
  });
  const edit = (u) => {
    setEditing(u.id);
    setF({
      ...blank,
      first_name: u.first_name,
      last_name: u.last_name,
      email: u.email,
      username: u.username,
      student_number: u.student_number || "",
      student_phone: u.student_phone || "",
      staff_number: u.staff_number || "",
      instructor_phone: u.instructor_phone || "",
    });
  };
  const field = (k, p, type = "text", required = false) => (
    <input
      type={type}
      placeholder={p}
      aria-label={p}
      required={required}
      value={f[k]}
      onChange={(e) => setF({ ...f, [k]: e.target.value })}
    />
  );

  return (
    <>
      <form className="card row" onSubmit={(event) => { event.preventDefault(); save(); }}>
        {field("first_name", "First name", "text", true)}
        {field("last_name", "Last name")}
        {field("email", "Email", "email")}
        {field("username", "Username", "text", true)}
        {field("password", editing ? "New password (optional)" : "Password", "password", !editing)}
        {role === "student" && <>
          {field("student_number", "Student number")}
          {field("student_phone", "Phone")}
        </>}
        {role === "instructor" && <>
          {field("staff_number", "Staff number")}
          {field("instructor_phone", "Phone")}
        </>}
        <button className="btn">{editing ? "Save changes" : `Add ${role}`}</button>
        {editing && <button type="button" className="btn ghost" onClick={reset}>Cancel</button>}
      </form>
      {err && <p className="err">{err}</p>}
      <div className="card wrap">
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Username</th><th>{role === "student" ? "Student number" : "Staff number"}</th><th>Phone</th><th /></tr></thead>
          <tbody>
            {list.length === 0 && <tr><td colSpan="6" className="muted">No {role}s yet.</td></tr>}
            {list.map((u) => (
              <tr key={u.id}>
                <td>{[u.first_name, u.last_name].filter(Boolean).join(" ") || "—"}</td>
                <td>{u.email || "—"}</td><td>{u.username}</td>
                <td>{role === "student" ? u.student_number || "—" : u.staff_number || "—"}</td>
                <td>{role === "student" ? u.student_phone || "—" : u.instructor_phone || "—"}</td>
                <td className="row">
                  <button className="btn ghost" onClick={() => edit(u)}>Edit</button>
                  <button className="btn danger" onClick={() => run(() => api.delete(`/users/${u.id}/`))}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
