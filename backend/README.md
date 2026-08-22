# TNPSC Group 4 Learning API

Production-oriented FastAPI backend for the competitive-exam platform. It exposes versioned REST endpoints at `/api/v1`, Swagger at `/docs`, liveness at `/health/live`, readiness at `/health/ready`, and Prometheus metrics at `/metrics`.

## Start locally

1. Copy `.env.example` to `.env` and replace all secrets.
2. Run `docker compose up --build`.
3. Apply migrations with `alembic upgrade head` from the API container.

Copy `.env.example` first. The provided compose file supplies PostgreSQL and
Redis; never use its development credentials outside local development.

The architecture uses feature modules, async SQLAlchemy, repositories/services, JWT refresh sessions, soft deletion, RBAC permissions, audit records, and generic taxonomy/test content entities. Add Alembic revisions for all schema changes; `Base.metadata.create_all` is deliberately not used at application startup.

## Mobile APIs (TNPSC Group 4 + VAO)

## Dedicated TNPSC Group 4 course APIs

The `/api/v1/mobile/syllabus` endpoint returns the complete `subject → unit →
chapter` tree. `GET /mobile/chapters/{chapter_id}/content` returns videos,
PDFs and chapter tests, while `/mobile/course/tests/{test_id}/start`, `submit`, and
`leaderboard` handle a scored exam flow without exposing correct answers
before submission. All learner test endpoints require a JWT obtained through
the phone OTP endpoints.

Content operators use `/api/v1/admin/course/{subjects|units|chapters|videos|pdfs|tests}`
for CRUD, `/admin/course/questions` for question/options creation, and
`/admin/uploads` for authenticated file uploads. These routes require the
existing `content:write` or `questions:write` RBAC permissions. In development
uploads are served from `/uploads`; configure `S3_BUCKET` and `AWS_REGION` to
send assets to AWS S3 instead.

Flutter multipart uploads use `POST /api/v1/admin/course/videos/upload` with
`chapter_id`, `title_ta`, `title_en`, and a `video/*` `file`, or
`POST /api/v1/admin/course/pdfs/upload` with `chapter_id`, `title`, and an
`application/pdf` `file`. Both require `content:write`, validate the target
chapter, and stream the file instead of reading it into application memory.
Set `S3_PUBLIC_BASE_URL` to the public bucket or CDN origin when S3 is used.
Subjects, units, and chapters accept and return Flutter's `title_ta` and
`title_en` fields; question creation requires `chapter_id`.

- `POST /api/v1/auth/request-otp` and `POST /api/v1/auth/verify-otp` support phone sign-in. To test before configuring an SMS provider, set `OTP_LOG_CODES=true` temporarily and read the generated code in the API logs. Disable it before real users sign in; replace this temporary flow with an SMS provider before production.
- `GET /api/v1/mobile/pdfs` lists Free PDFs and `POST /api/v1/admin/pdfs` uploads a PDF for users with `content:write`.
- `GET /api/v1/mobile/tests?test_type=practice|smart_quiz|live` lists tests. Admins create them at `POST /api/v1/admin/tests`.
- Students start, resume, save answers, submit, analyse, review, and rank through `/api/v1/mobile/tests/{id}/start` and `/api/v1/mobile/attempts/{attempt_id}/*`.
- Test expiry is calculated on the server. Normal and smart-quiz tests resume while their server-side time continues. Live tests allow only one non-resumable attempt.

## Firebase push notifications

The backend sends FCM topic notifications to `tnpsc_all` when an admin uploads a PDF, creates a standard/smart test, or announces a live test. Set `FIREBASE_CREDENTIALS_PATH` to the **absolute server-only path** of the Firebase Admin service-account JSON. Do not place that file in the repository or Flutter project. Flutter clients subscribe to `tnpsc_all` after notification permission is granted.

## Flutter Web login

`POST /api/v1/auth/login` accepts a JSON **object**, not form data or a JSON-encoded string. Send `Content-Type: application/json` and pass a map directly to Dio:

```dart
final response = await dio.post(
  '$apiBaseUrl/api/v1/auth/login',
  data: {
    'email': email,
    'password': password,
    'device_name': 'flutter-web',
  },
  options: Options(contentType: Headers.jsonContentType),
);
```

Do not call `jsonEncode` on the map when using Dio; double-encoding produces a JSON string and FastAPI responds with `422 Input should be a valid dictionary or object`.

For local Flutter Web, the default CORS policy permits `localhost` and `127.0.0.1` on any port. For production, set `CORS_ORIGINS` to a comma-separated list of exact frontend origins, such as `https://app.example.com`; do not use `*` when credentials are enabled.

## Deploy to Render

The repository root contains `render.yaml`. In Render, select **New > Blueprint**, connect this repository, and select the blueprint. Render creates the `exam-platform-api` Docker web service and managed PostgreSQL database, passing the database's private connection string to `DATABASE_URL`.

During Blueprint creation, provide `REDIS_URL` (a TLS Redis URL from Render Key Value or another provider) and `CORS_ORIGINS` (the exact frontend origin, for example `https://your-admin.onrender.com`). If the frontend uses a variable trusted hostname, set the optional anchored `CORS_ORIGIN_REGEX` instead (for example `^https://your-admin-app\\.onrender\\.com$`). Keep the generated `JWT_SECRET_KEY` private. The Blueprint runs `alembic upgrade head` as its pre-deploy command.

## Commerce and content operations

- `/api/v1/plans` and `/api/v1/payments/*` provide plan discovery, Razorpay orders, signature verification, webhook verification, invoices, and subscriptions. Values are integer paise.
- `/api/v1/questions/import` and `/api/v1/questions/export` provide the Excel bulk-content workflow; export produces the import template.
- Device registration, broadcast notifications, protected video publishing, user analytics, and dashboard totals are available under `/api/v1/devices`, `/api/v1/admin/*`, and `/api/v1/users/*`.
- Production must set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `JWT_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, and `CORS_ORIGINS` (and, if needed, `CORS_ORIGIN_REGEX`), then run `alembic upgrade head`.
