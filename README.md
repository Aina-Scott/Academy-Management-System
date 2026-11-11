# Academy Management System

React + Vite frontend, Django REST Framework backend, JWT auth, PostgreSQL (SQLite fallback for quick local runs).

Database and schema documentation: [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md)

## Backend
In PowerShell, open the backend folder, set local-only development settings, then run migrations and the API:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DEBUG = "1"
$env:CORS_ORIGINS = "http://localhost:5173"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
The API is available at `http://localhost:8000/api/`. Superusers get the admin role automatically. PostgreSQL: set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` (and optionally `DB_PORT`) before running migrations. Without `DB_NAME` the app uses SQLite.

To set or replace an admin password, run `python manage.py changepassword <username>`. Any old default development password is disabled; reset the account password before signing in.

## Frontend
```bash
cd frontend
npm install
npm run dev                                        # http://localhost:5173
```
Set `VITE_API_URL` if the API is not at `http://localhost:8000/api`.

## Roles
- **admin**: manages students, instructors, courses and enrollments
- **instructor**: sees own courses and their enrolled students
- **student**: browses courses, enrolls and drops

Student and instructor records support optional student/staff numbers and phone numbers. Local development defaults to `DEBUG=1` so the Vite frontend can call Django over HTTP. Configure production with a persistent `SECRET_KEY`, `DEBUG=0`, the deployed hostnames in `ALLOWED_HOSTS`, and the frontend origin(s) in `CORS_ORIGINS`. Secure cookies and HTTPS redirects are enabled when debug mode is off.

## Attendance
Admins can take or correct attendance for any course; instructors can do so only for courses assigned to them. Students can view only their own history and summary. There is one session per course per day, with a required Present or Absent status for every enrolled student. The percentage is `Present / (Present + Absent) * 100`; an empty report has no percentage. Corrections update the recorded staff member and timestamp.

Attendance API routes include `GET/POST /api/attendance/sessions/`, `GET/POST /api/attendance/sessions/{id}/records/`, `PATCH /api/attendance/records/{id}/`, `GET /api/attendance/my-history/`, and `GET /api/attendance/reports/`.
