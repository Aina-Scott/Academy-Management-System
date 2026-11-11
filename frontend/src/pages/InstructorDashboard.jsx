import { useEffect, useState } from "react";
import api, { errMsg } from "../services/api";

export default function InstructorDashboard({ user }) {
  const [courses, setCourses] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([api.get("/courses/"), api.get("/enrollments/")])
      .then(([courseResponse, enrollmentResponse]) => {
        setCourses(courseResponse.data);
        setEnrollments(enrollmentResponse.data);
      })
      .catch((error) => setErr(errMsg(error)));
  }, []);

  return (
    <>
      <p className="muted">Welcome, {user.first_name || user.username}.</p>
      {err && <p className="err">{err}</p>}
      <div className="stats">
        <section className="card stat"><strong>{courses.length}</strong><span className="muted">Assigned courses</span></section>
        <section className="card stat"><strong>{enrollments.length}</strong><span className="muted">Student enrollments</span></section>
      </div>
      <div className="card wrap">
        <h2>Enrolled students</h2>
        <table>
          <thead><tr><th>Student</th><th>Course</th><th>Code</th></tr></thead>
          <tbody>
            {enrollments.length === 0 && <tr><td colSpan="3" className="muted">No students enrolled in your courses yet.</td></tr>}
            {enrollments.map((enrollment) => (
              <tr key={enrollment.id}><td>{enrollment.student_name}</td><td>{enrollment.course_title}</td><td>{enrollment.course_code}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}