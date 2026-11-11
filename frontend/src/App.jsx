import { useEffect, useState } from "react";
import { currentUser, hasToken, logout } from "./services/api";
import Login from "./pages/Login.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";
import Courses from "./pages/Courses.jsx";
import Student from "./pages/Student.jsx";
import Enrollments from "./pages/Enrollments.jsx";
import InstructorDashboard from "./pages/InstructorDashboard.jsx";
import StudentDashboard from "./pages/StudentDashboard.jsx";
import Attendance from "./pages/Attendance.jsx";

const TABS = {
  admin: ["Dashboard", "Courses", "Students", "Instructors", "Enrollments", "Attendance"],
  instructor: ["Dashboard", "Courses", "Enrollments", "Attendance"],
  student: ["Dashboard", "Courses", "Enrollments", "Attendance"],
};
const TITLES = {
  Dashboard: "Dashboard",
  Courses: "Courses",
  Enrollments: "Enrollments",
  Students: "Students",
  Instructors: "Instructors",
  Attendance: "Attendance",
};

export default function App() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!hasToken());
  const [tab, setTab] = useState("Dashboard");
  const [attendanceDirty, setAttendanceDirty] = useState(false);

  useEffect(() => {
    if (hasToken()) currentUser().then(setUser).catch(logout).finally(() => setReady(true));
  }, []);

  if (!ready) return null;
  if (!user) return <Login onLogin={(u) => { setUser(u); setTab("Dashboard"); }} />;

  const navigate = (nextTab) => {
    if (nextTab === tab) return;
    if (tab === "Attendance" && attendanceDirty && !window.confirm("Discard unsaved attendance changes?")) return;
    setAttendanceDirty(false);
    setTab(nextTab);
  };
  const out = () => {
    if (tab === "Attendance" && attendanceDirty && !window.confirm("Discard unsaved attendance changes?")) return;
    setAttendanceDirty(false);
    logout();
    setUser(null);
  };
  const page = {
    Dashboard: user.role === "admin"
      ? <AdminDashboard />
      : user.role === "instructor"
        ? <InstructorDashboard user={user} />
        : <StudentDashboard user={user} />,
    Courses: <Courses user={user} />,
    Enrollments: <Enrollments user={user} />,
    Students: <Student role="student" />,
    Instructors: <Student role="instructor" />,
    Attendance: <Attendance user={user} onDirtyChange={setAttendanceDirty} />,
  }[tab];

  return (
    <div className="app">
      <nav>
        <strong className="brand">Academy</strong>
        {TABS[user.role].map((t) => (
          <button key={t} className={t === tab ? "on" : ""} onClick={() => navigate(t)}>{TITLES[t]}</button>
        ))}
      </nav>
      <main>
        <header>
          <h1>{TITLES[tab]}</h1>
          <div className="row">
            <span className="muted">{user.first_name || user.username} ({user.role})</span>
            <button className="btn ghost" onClick={out}>Sign out</button>
          </div>
        </header>
        {page}
      </main>
    </div>
  );
}
