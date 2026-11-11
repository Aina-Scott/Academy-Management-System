import { useEffect, useState } from "react";
import api, { errMsg } from "../services/api";

export default function StudentDashboard({ user }) {
  const [profile, setProfile] = useState(null);
  const [enrollments, setEnrollments] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([api.get("/me/"), api.get("/enrollments/")])
      .then(([profileResponse, enrollmentResponse]) => {
        setProfile(profileResponse.data);
        setEnrollments(enrollmentResponse.data);
      })
      .catch((error) => setErr(errMsg(error)));
  }, []);

  return (
    <>
      <p className="muted">Welcome, {user.first_name || user.username}.</p>
      {err && <p className="err">{err}</p>}
      <section className="card">
        <h2>My profile</h2>
        {profile ? (
          <dl className="profile">
            <dt>Name</dt><dd>{[profile.first_name, profile.last_name].filter(Boolean).join(" ") || "—"}</dd>
            <dt>Email</dt><dd>{profile.email || "—"}</dd>
            <dt>Student number</dt><dd>{profile.student_number || "—"}</dd>
            <dt>Phone</dt><dd>{profile.student_phone || "—"}</dd>
          </dl>
        ) : <p className="muted">Loading profile…</p>}
      </section>
      <section className="card wrap">
        <h2>My courses</h2>
        <table>
          <thead><tr><th>Course</th><th>Code</th></tr></thead>
          <tbody>
            {enrollments.length === 0 && <tr><td colSpan="2" className="muted">You are not enrolled in any courses.</td></tr>}
            {enrollments.map((enrollment) => (
              <tr key={enrollment.id}><td>{enrollment.course_title}</td><td>{enrollment.course_code}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}