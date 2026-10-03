# Shivir Lite API

A Django REST Framework backend API for managing events, participant registrations, attendance, and reporting. Built using Python 3.12+, Django 5.x, DRF 3.15+, and PostgreSQL, structured entirely with class-based DRF `APIView` endpoints.

---

## Architecture Overview

All endpoints are built using explicit class-based `rest_framework.views.APIView` classes (no `ViewSet` or `routers`).

- **`EventListCreateAPIView`**: `GET /api/events/`, `POST /api/events/`
- **`EventDetailAPIView`**: `GET /api/events/<uuid:pk>/`, `PUT /api/events/<uuid:pk>/`, `PATCH /api/events/<uuid:pk>/`, `DELETE /api/events/<uuid:pk>/`
- **`EventRegisterAPIView`**: `POST /api/events/<uuid:event_id>/register/`
- **`EventAttendanceAPIView`**: `POST /api/events/<uuid:event_id>/attendance/`
- **`EventRegistrationsAPIView`**: `GET /api/events/<uuid:event_id>/registrations/`
- **`EventSummaryAPIView`**: `GET /api/events/<uuid:event_id>/summary/`

---

## Requirements

- Python 3.12+
- Django 5.x
- Django REST Framework 3.15+
- PostgreSQL (database: `shivir_lite`, user: `postgres`, host: `localhost`, port: `5432`)
- pytest & pytest-django

---

## Environment Variables (.env)

Configure PostgreSQL connection in `.env`:

```env
DATABASE_URL=postgresql://postgres:7499@localhost:5432/shivir_lite
DB_NAME=shivir_lite
DB_USER=postgres
DB_PASSWORD=7499
DB_HOST=localhost
DB_PORT=5432
```

---

## Setup & Installation

Run the following commands in PowerShell from the repository root:

```powershell
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply database migrations
python .\shivirlite\manage.py migrate

# 4. Create staff and regular users with tokens
python .\shivirlite\manage.py create_users

# 5. Run local development server
python .\shivirlite\manage.py runserver
```

---

## Testing

Run the full pytest suite:

```powershell
python -m pytest
```

---

## Authentication

Authentication is handled via **TokenAuthentication** (`Authorization: Token <token>`) or **SessionAuthentication**.

Users are seeded via `python manage.py create_users`:
- **Staff User**: `username=staff`, `password=StaffPass123!`, `is_staff=True`
- **Regular User**: `username=regular`, `password=UserPass123!`, `is_staff=False`

To retrieve a token via API:
`POST /api/token/` with payload `{"username": "staff", "password": "StaffPass123!"}`.

---

## API Endpoints

| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| `GET` | `/api/events/` | Authenticated | List events with pagination (20/page). Regular users see published only. Staff see all. Filters: `?is_published=true\|false`, `?start_date_after=YYYY-MM-DD`. |
| `POST` | `/api/events/` | Staff Only | Create a new event. |
| `GET` | `/api/events/<uuid:pk>/` | Authenticated | Retrieve event details. Regular users receive 404 for unpublished events. |
| `PUT` | `/api/events/<uuid:pk>/` | Staff Only | Full event update. |
| `PATCH` | `/api/events/<uuid:pk>/` | Staff Only | Partial event update. |
| `DELETE` | `/api/events/<uuid:pk>/` | Staff Only | Delete event (204 No Content). |
| `POST` | `/api/events/<uuid:event_id>/register/` | Authenticated | Register participant with phone normalization and duplicate protection. |
| `POST` | `/api/events/<uuid:event_id>/attendance/` | Staff Only | Idempotently mark attendance for participants by date. |
| `GET` | `/api/events/<uuid:event_id>/registrations/` | Staff Only | List registrations with `days_attended` and `admin_note` (constant SQL queries). |
| `GET` | `/api/events/<uuid:event_id>/summary/` | Staff Only | Aggregated statistics (`registered`, `cancelled`, `attended_at_least_once`, `attended_every_day`, `revenue`). |

---

## Task Status

- **Task 1 — Event CRUD, access rules, pagination, filtering, and validation**: Complete (Pure APIViews).
- **Task 2 — Phone-normalized event registration**: Complete (E.164 parsing, participant reuse).
- **Task 3 — Concurrency safety & duplicate protection**: Complete (`select_for_update`, conditional `UniqueConstraint`).
- **Task 4 — Idempotent attendance marking**: Complete (Batch processing, unique constraint on registration + date).
- **Task 5 — Staff registration list with constant query count**: Complete (`select_related`, `annotate(Count('attendances'))` avoiding N+1).
- **Task 6 — Aggregated event summary**: Complete (Pure database aggregation using `Sum`, `Count`, `Q`, `Coalesce`, Decimal money formatting).
- **Optional bonus tasks**: Not implemented per project instructions.

---

## Concurrency (Task 3)

Without a transaction and row-level locking, two concurrent requests can both read the same remaining event capacity simultaneously and both pass the capacity check, causing overbooking. A database transaction wrapping `select_for_update()` serializes access to the `Event` row in PostgreSQL, guaranteeing atomic capacity verification before creating a registration. Furthermore, a database-level conditional `UniqueConstraint` on `(participant, event)` where `status = 'CONFIRMED'` prevents race conditions from creating duplicate confirmed registrations even under extreme concurrent requests.

---

## Assumptions

- Registrations are only allowed for published events before their `end_date`.
- A participant's initial `amount_paid` matches the event `fee`.
- Regular users requesting unpublished events receive HTTP 404 to avoid leaking event existence.
- All monetary amounts use `DecimalField` and formatted strings to exactly 2 decimal places (never floats).

---

## Approximate Hours Spent

Hours spent: **6 hours**
