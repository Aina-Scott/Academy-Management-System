import { useEffect, useMemo, useState } from "react";
import api, { errMsg } from "../services/api";

const today = () => {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
};

function Summary({ report }) {
  if (!report) return null;
  return (
    <div className="stats">
      <section className="card stat"><strong>{report.present}</strong><span className="muted">Present</span></section>
      <section className="card stat"><strong>{report.absent}</strong><span className="muted">Absent</span></section>
      <section className="card stat"><strong>{report.attendance_percentage == null ? "—" : `${report.attendance_percentage}%`}</strong><span className="muted">Attendance</span></section>
      <section className="card stat"><strong>{report.total_records}</strong><span className="muted">Recorded</span></section>
    </div>
  );
}

function HistoryTable({ rows, emptyMessage }) {
  return (
    <div className="card wrap">
      <table>
        <thead><tr><th>Date</th><th>Course</th><th>Student</th><th>Status</th><th>Last updated by</th><th>Updated</th></tr></thead>
        <tbody>
          {rows.length === 0 && <tr><td colSpan="6" className="muted">{emptyMessage}</td></tr>}
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.date}</td>
              <td>{row.course_code} — {row.course_title}</td>
              <td>{row.student_name}</td>
              <td>{row.status}</td>
              <td>{row.marked_by_name}</td>
              <td>{new Date(row.marked_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StudentAttendance() {
  const [rows, setRows] = useState([]);
  const [report, setReport] = useState(null);
  const [courses, setCourses] = useState([]);
  const [course, setCourse] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setErr("");
      const params = {
        ...(course ? { course } : {}),
        ...(dateFrom ? { date_from: dateFrom } : {}),
        ...(dateTo ? { date_to: dateTo } : {}),
      };
      const [history, summary] = await Promise.all([
        api.get("/attendance/my-history/", { params }),
        api.get("/attendance/reports/", { params }),
      ]);
      setRows(history.data);
      setReport(summary.data);
    } catch (error) {
      setErr(errMsg(error));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    api.get("/attendance/my-history/")
      .then(({ data }) => {
        setCourses([...new Map(data.map((row) => [row.course, {
          id: row.course,
          code: row.course_code,
          title: row.course_title,
        }])).values()]);
      })
      .catch((error) => setErr(errMsg(error)));
  }, []);

  useEffect(() => { load(); }, [course, dateFrom, dateTo]);

  return (
    <>
      <form className="card row" onSubmit={(event) => { event.preventDefault(); load(); }}>
        <select aria-label="Course" value={course} onChange={(event) => setCourse(event.target.value)}>
          <option value="">All courses</option>
          {courses.map((item) => <option key={item.id} value={item.id}>{item.code} — {item.title}</option>)}
        </select>
        <label>From <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></label>
        <label>To <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></label>
        <button className="btn" disabled={loading}>Apply filters</button>
      </form>
      {err && <p className="err">{err}</p>}
      {report && <Summary report={report} />}
      <HistoryTable rows={rows} emptyMessage={loading ? "Loading attendance…" : "No attendance records for these filters."} />
    </>
  );
}

function StaffAttendance({ onDirtyChange }) {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [sessionDate, setSessionDate] = useState(today);
  const [session, setSession] = useState(null);
  const [roster, setRoster] = useState([]);
  const [history, setHistory] = useState([]);
  const [report, setReport] = useState(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [dirty, setDirty] = useState(false);
  const [err, setErr] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => { onDirtyChange(dirty); }, [dirty, onDirtyChange]);

  const sessionReport = useMemo(() => {
    const present = roster.filter((row) => row.status === "present").length;
    const absent = roster.filter((row) => row.status === "absent").length;
    const total = present + absent;
    return {
      present,
      absent,
      total_records: total,
      attendance_percentage: total ? Math.round((present / total) * 1000) / 10 : null,
    };
  }, [roster]);

  const loadHistory = async () => {
    if (!courseId) return;
    const params = {
      course: courseId,
      ...(dateFrom ? { date_from: dateFrom } : {}),
      ...(dateTo ? { date_to: dateTo } : {}),
    };
    try {
      const [historyResponse, reportResponse] = await Promise.all([
        api.get("/attendance/my-history/", { params }),
        api.get("/attendance/reports/", { params }),
      ]);
      setHistory(historyResponse.data);
      setReport(reportResponse.data);
    } catch (error) {
      setErr(errMsg(error));
    }
  };

  useEffect(() => {
    api.get("/courses/")
      .then(({ data }) => {
        setCourses(data);
        if (data.length) setCourseId(String(data[0].id));
      })
      .catch((error) => setErr(errMsg(error)));
  }, []);

  useEffect(() => { loadHistory(); }, [courseId, dateFrom, dateTo]);

  useEffect(() => {
    if (!dirty) return undefined;
    const warn = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const openSession = async (event) => {
    event.preventDefault();
    if (!courseId) return;
    if (dirty && !window.confirm("Discard unsaved attendance changes?")) return;
    setLoading(true);
    setErr("");
    setMessage("");
    try {
      const response = await api.post("/attendance/sessions/", {
        course: Number(courseId),
        date: sessionDate,
      });
      const opened = response.data;
      const { data: classList } = await api.get(`/attendance/sessions/${opened.id}/records/`);
      setSession(opened);
      setRoster(classList);
      setDirty(false);
      setMessage(response.status === 201 ? "New session opened." : "Existing session opened. Records are ready to review.");
    } catch (error) {
      setErr(errMsg(error));
    } finally {
      setLoading(false);
    }
  };

  const changeStatus = (studentId, status) => {
    setRoster((current) => current.map((row) => row.student === studentId ? { ...row, status } : row));
    setDirty(true);
    setMessage("");
  };

  const save = async (event) => {
    event.preventDefault();
    if (!session) return;
    if (roster.some((row) => !row.status)) {
      setErr("Choose Present or Absent for every enrolled student before saving.");
      return;
    }
    setLoading(true);
    setErr("");
    try {
      const { data } = await api.post(`/attendance/sessions/${session.id}/records/`, {
        records: roster.map(({ student, status }) => ({ student, status })),
      });
      setRoster(data);
      setDirty(false);
      setMessage("Attendance saved. Corrections are recorded with the editor and time.");
      await loadHistory();
    } catch (error) {
      setErr(errMsg(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <form className="card row" onSubmit={openSession}>
        <select aria-label="Course" required value={courseId} onChange={(event) => {
          if (dirty && !window.confirm("Discard unsaved attendance changes?")) return;
          setCourseId(event.target.value);
          setSession(null);
          setRoster([]);
          setDirty(false);
        }}>
          {courses.length === 0 && <option value="">No assigned courses</option>}
          {courses.map((item) => <option key={item.id} value={item.id}>{item.code} — {item.title}</option>)}
        </select>
        <label>Class date <input type="date" required value={sessionDate} onChange={(event) => {
          if (dirty && !window.confirm("Discard unsaved attendance changes?")) return;
          setSessionDate(event.target.value);
          setSession(null);
          setRoster([]);
          setDirty(false);
        }} /></label>
        <button className="btn" disabled={loading || !courseId}>Open session</button>
      </form>
      {err && <p className="err">{err}</p>}
      {message && <p className="success">{message}</p>}
      {session && (
        <form className="card wrap" onSubmit={save}>
          <h2>{session.course_code} — {session.course_title} · {session.date}</h2>
          {roster.length === 0
            ? <p className="muted">No students are currently enrolled in this course.</p>
            : <table>
              <thead><tr><th>Student</th><th>Student number</th><th>Attendance</th><th>Last marked by</th></tr></thead>
              <tbody>
                {roster.map((row) => (
                  <tr key={row.student}>
                    <td>{row.student_name}</td>
                    <td>{row.student_number || "—"}</td>
                    <td>
                      <select required aria-label={`Attendance for ${row.student_name}`} value={row.status || ""} onChange={(event) => changeStatus(row.student, event.target.value)}>
                        <option value="" disabled>Choose status</option>
                        <option value="present">Present</option>
                        <option value="absent">Absent</option>
                      </select>
                    </td>
                    <td>{row.marked_by || "Not saved"}</td>
                  </tr>
                ))}
              </tbody>
            </table>}
          {roster.length > 0 && <button className="btn" disabled={loading}>{dirty ? "Save attendance" : "Save corrections"}</button>}
        </form>
      )}
      {session && roster.length > 0 && <Summary report={sessionReport} />}
      <section className="card">
        <h2>Course history and report</h2>
        <div className="row">
          <label>From <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></label>
          <label>To <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></label>
        </div>
      </section>
      {report && <Summary report={report} />}
      <HistoryTable rows={history} emptyMessage="No attendance records for this course and date range." />
    </>
  );
}

export default function Attendance({ user, onDirtyChange }) {
  return user.role === "student"
    ? <StudentAttendance />
    : <StaffAttendance onDirtyChange={onDirtyChange} />;
}
