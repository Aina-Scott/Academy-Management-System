import { useEffect, useState } from "react";
import api, { errMsg } from "../services/api";

export default function Enrollments({ user }) {
  const [rows, setRows] = useState([]);
  const [students, setStudents] = useState([]);
  const [courses, setCourses] = useState([]);
  const [s, setS] = useState("");
  const [c, setC] = useState("");
  const [err, setErr] = useState("");
  const isAdmin = user.role === "admin";

  const load = async () => {
    setRows((await api.get("/enrollments/")).data);
    if (isAdmin) {
      setStudents((await api.get("/users/?role=student")).data);
      setCourses((await api.get("/courses/")).data);
    }
  };
  useEffect(() => { load().catch((e) => setErr(errMsg(e))); }, []);

  const run = async (fn) => {
    try { setErr(""); await fn(); await load(); } catch (e) { setErr(errMsg(e)); }
  };

  return (
    <>
      {isAdmin && (
        <div className="card row">
          <select value={s} onChange={(e) => setS(e.target.value)}>
            <option value="">Student</option>
            {students.map((x) => <option key={x.id} value={x.id}>{x.first_name || x.username}</option>)}
          </select>
          <select value={c} onChange={(e) => setC(e.target.value)}>
            <option value="">Course</option>
            {courses.map((x) => <option key={x.id} value={x.id}>{x.code} {x.title}</option>)}
          </select>
          <button className="btn" onClick={() => run(() => api.post("/enrollments/", { student: s || undefined, course: c }))}>Enroll student</button>
        </div>
      )}
      {err && <p className="err">{err}</p>}
      <div className="card wrap">
        <table>
          <thead><tr><th>Student</th><th>Course</th><th /></tr></thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan="3" className="muted">No enrollments yet.</td></tr>}
            {rows.map((e) => (
              <tr key={e.id}>
                <td>{e.student_name}</td><td>{e.course_code}</td>
                <td>{user.role !== "instructor" && (
                  <button className="btn ghost" onClick={() => run(() => api.delete(`/enrollments/${e.id}/`))}>Remove</button>)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
