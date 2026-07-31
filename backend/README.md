# Exam Platform API

Production-oriented FastAPI backend for the competitive-exam platform. It exposes versioned REST endpoints at `/api/v1`, Swagger at `/docs`, liveness at `/health/live`, readiness at `/health/ready`, and Prometheus metrics at `/metrics`.

## Start locally

1. Copy `.env.example` to `.env` and replace all secrets.
2. Run `docker compose up --build`.
3. Apply migrations with `alembic upgrade head` from the API container.

The architecture uses feature modules, async SQLAlchemy, repositories/services, JWT refresh sessions, soft deletion, RBAC permissions, audit records, and generic taxonomy/test content entities. Add Alembic revisions for all schema changes; `Base.metadata.create_all` is deliberately not used at application startup.

## Deploy to Render

The repository root contains `render.yaml`. In Render, select **New > Blueprint**, connect this repository, and select the blueprint. Render creates the `exam-platform-api` Docker web service and managed PostgreSQL database, passing the database's private connection string to `DATABASE_URL`.

During Blueprint creation, provide `REDIS_URL` (a TLS Redis URL from Render Key Value or another provider) and `CORS_ORIGINS` (the exact frontend origin, for example `https://your-admin.onrender.com`). Keep the generated `JWT_SECRET_KEY` private. After the first deploy, run `alembic upgrade head` from a Render Shell before creating users or content.
