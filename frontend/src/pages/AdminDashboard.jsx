import { useEffect, useState } from "react";
import api, { errMsg } from "../services/api";

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([
      api.get("/users/"),
      api.get("/courses/"),
      api.get("/enrollments/"),
    ])
      .then(([users, courses, enrollments]) => setSummary({
        students: users.data.filter((user) => user.role === "student").length,
        instructors: users.data.filter((user) => user.role === "instructor").length,
        courses: courses.data.length,
        enrollments: enrollments.data.length,
      }))
      .catch((error) => setErr(errMsg(error)));
  }, []);

  if (err) return <p className="err">{err}</p>;
  if (!summary) return <p className="muted">Loading dashboard…</p>;

  return (
    <div className="stats">
      {Object.entries(summary).map(([label, count]) => (
        <section className="card stat" key={label}>
          <strong>{count}</strong>
          <span className="muted">{label}</span>
        </section>
      ))}
    </div>
  );
}