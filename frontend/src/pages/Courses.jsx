import { useEffect, useState } from "react";
import api, { errMsg } from "../services/api";

const blank = { code: "", title: "", instructor: "", capacity: 30 };

export default function Courses({ user }) {
  const [courses, setCourses] = useState([]);
  const [mine, setMine] = useState([]);
  const [instructors, setInstructors] = useState([]);
  const [f, setF] = useState(blank);
  const [editing, setEditing] = useState(null);
  const [err, setErr] = useState("");
  const isAdmin = user.role === "admin";

  const load = async () => {
    setCourses((await api.get("/courses/")).data);
    if (user.role === "student") setMine((await api.get("/enrollments/")).data);
    if (isAdmin) setInstructors((await api.get("/users/?role=instructor")).data);
  };
  useEffect(() => { load().catch((e) => setErr(errMsg(e))); }, []);

  const run = async (fn) => {
    try { setErr(""); await fn(); await load(); } catch (e) { setErr(errMsg(e)); }
  };
  const reset = () => { setF(blank); setEditing(null); };
  const save = () => run(async () => {
    const data = { ...f, capacity: Number(f.capacity), instructor: f.instructor || null };
    if (editing) await api.patch(`/courses/${editing}/`, data);
    else await api.post("/courses/", data);
    reset();
  });
  const edit = (course) => {
    setEditing(course.id);
    setF({
      code: course.code,
      title: course.title,
      instructor: course.instructor || "",
      capacity: course.capacity,
    });
  };
  const enrollmentFor = (c) => mine.find((e) => e.course === c.id);

  return (
    <>
      {isAdmin && (
        <form className="card row" onSubmit={(event) => { event.preventDefault(); save(); }}>
          <input placeholder="Code" aria-label="Code" required value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} />
          <input placeholder="Title" aria-label="Title" required value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} />
          <select value={f.instructor} onChange={(e) => setF({ ...f, instructor: e.target.value })}>
            <option value="">No instructor</option>
            {instructors.map((i) => <option key={i.id} value={i.id}>{i.first_name || i.username}</option>)}
          </select>
          <input type="number" min="1" required className="narrow" aria-label="Capacity" value={f.capacity} onChange={(e) => setF({ ...f, capacity: e.target.value })} />
          <button className="btn">{editing ? "Save changes" : "Add course"}</button>
          {editing && <button type="button" className="btn ghost" onClick={reset}>Cancel</button>}
        </form>
      )}
      {err && <p className="err">{err}</p>}
      <div className="card wrap">
        <table>
          <thead><tr><th>Code</th><th>Title</th><th>Instructor</th><th>Seats</th><th /></tr></thead>
          <tbody>
            {courses.length === 0 && <tr><td colSpan="5" className="muted">No courses yet.</td></tr>}
            {courses.map((c) => {
              const en = enrollmentFor(c);
              return (
                <tr key={c.id}>
                  <td>{c.code}</td><td>{c.title}</td><td>{c.instructor_name || "Unassigned"}</td>
                  <td>{c.enrolled} / {c.capacity}</td>
                  <td>
                    {isAdmin && <>
                      <button className="btn ghost" onClick={() => edit(c)}>Edit</button>
                      <button className="btn danger" onClick={() => run(() => api.delete(`/courses/${c.id}/`))}>Delete</button>
                    </>}
                    {user.role === "student" && (en
                      ? <button className="btn ghost" onClick={() => run(() => api.delete(`/enrollments/${en.id}/`))}>Drop</button>
                      : <button className="btn" onClick={() => run(() => api.post("/enrollments/", { course: c.id }))}>Enroll</button>)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
