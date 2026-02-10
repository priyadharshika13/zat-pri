# Deployment View

## Container Architecture

The application is deployed as containerized services using Docker.

## Backend Container

**Base Image:** `python:3.11-slim`

**Multi-Stage Build:**
- Stage 1 (builder): Installs Python dependencies
- Stage 2 (production): Copies dependencies and application code

**Container Configuration:**
- Non-root user (`appuser`, UID 1000)
- Working directory: `/app`
- Exposed port: `8000`
- Health check: HTTP GET `/api/v1/health` every 30 seconds

**Application Server:**
- Gunicorn with Uvicorn workers
- Worker count: `CPU_COUNT * 2 + 1` (configurable via `GUNICORN_WORKERS`)
- Worker class: `uvicorn.workers.UvicornWorker`
- Preload app: Enabled for better performance
- Graceful timeout: 30 seconds

**Volumes:**
- `/app/logs`: Application logs
- `/app/certs`: Certificate storage (read-only)
- Database: External PostgreSQL or SQLite file

## Frontend Deployment

**Build Process:**
- Vite builds React application to static assets
- Output directory: `frontend/dist/`
- Static files served via web server or CDN

**Deployment Options:**
- Static file hosting (Nginx, Apache, CDN)
- Containerized with Nginx (optional)
- No backend dependencies at runtime

## Database Deployment

**Production:**
- PostgreSQL instance (separate container or managed service)
- Connection via `DATABASE_URL` environment variable
- SSL/TLS required for production connections

**Development:**
- SQLite file (local development only)
- File path: `backend/zatca.db`
- Not suitable for production

## Docker Compose Configuration

**Services:**
- `zatca-api`: Backend API container
- Database: External PostgreSQL (not in compose file)

**Environment Variables:**
- `ENVIRONMENT_NAME`: `production` or `development`
- `ZATCA_ENV`: `SANDBOX` or `PRODUCTION`
- `DATABASE_URL`: PostgreSQL connection string
- `GUNICORN_WORKERS`: Worker process count
- `GUNICORN_TIMEOUT`: Request timeout (seconds)

**Volume Mounts:**
- Certificate storage: `../backend/certs:/app/certs:ro`
- Logs: `../backend/logs:/app/logs`
- Database: `../backend/zatca.db:/app/zatca.db` (SQLite only)

**Health Checks:**
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3
- Start period: 40 seconds

## Deployment Environments

### Development

**Configuration:**
- `ENVIRONMENT_NAME=development`
- `DEBUG=true`
- `ENABLE_DOCS=true`
- `ZATCA_ENV=SANDBOX`
- SQLite database (optional)

**Deployment:**
- Local Docker Compose
- Direct Python execution (`python run_dev.py`)
- Hot reload enabled

### Production

**Configuration:**
- `ENVIRONMENT_NAME=production`
- `DEBUG=false`
- `ENABLE_DOCS=false`
- `ZATCA_ENV=PRODUCTION` (or `SANDBOX` for testing)
- PostgreSQL database (required)

**Deployment:**
- Container orchestration (Docker Compose, Kubernetes, ECS)
- Load balancer for high availability
- Database backups and replication
- SSL/TLS termination at load balancer

## Database Migrations

**Tool:** Alembic

**Migration Process:**
1. Generate migration: `alembic revision --autogenerate -m "description"`
2. Review migration script
3. Apply migration: `alembic upgrade head`
4. Rollback if needed: `alembic downgrade -1`

**Deployment Integration:**
- Migrations run on container startup (optional)
- Manual migration execution (recommended for production)
- Migration scripts stored in `backend/alembic/versions/`

## Certificate Management

**Storage:**
- Certificates stored in `/app/certs/` directory
- Per-tenant, per-environment subdirectories
- Format: `{tenant_id}/{environment}/cert.pem` and `key.pem`

**Upload Process:**
- Certificates uploaded via API endpoint
- Validated for format and expiration
- Cryptographic verification: Private key matches certificate
- Old certificates deactivated on new upload
- Certificate metadata stored in database

**Onboarding Process:**
- Sandbox: Automated Compliance CSID API
- Production: OTP-based onboarding flow
- Both: Automatic certificate storage after validation

**Security:**
- Certificates mounted as read-only volume
- Private keys never exposed in API responses
- Certificate access restricted to tenant

## Logging Configuration

**Log Format:**
- JSON format for structured logging
- Log level: `INFO` (production), `DEBUG` (development)
- Log destination: stdout/stderr (container logs)

**Log Rotation:**
- Handled by container orchestration or log aggregation
- Log retention: Configurable via retention policy
- Sensitive data masked in logs

## Monitoring and Health Checks

**Health Endpoint:**
- `GET /api/v1/health`: Basic health check
- `GET /api/v1/system/health`: Detailed system health

**Health Check Components:**
- Database connectivity
- ZATCA API connectivity (optional)
- Application uptime
- Memory usage

**Container Health:**
- Docker health check configured
- Health check interval: 30 seconds
- Unhealthy containers restarted automatically

## Scaling Configuration

**Vertical Scaling:**
- Increase `GUNICORN_WORKERS` environment variable
- Adjust worker timeout for longer operations
- Increase container memory limits

**Horizontal Scaling:**
- Multiple container instances behind load balancer
- Stateless application design enables horizontal scaling
- Database connection pooling handles multiple instances
- Rate limiting per tenant (in-memory, not shared)

**Current Limitations:**
- Rate limiting buckets stored in-memory (not shared across instances)
- Certificate storage on filesystem (not shared across instances)
- Future: Redis for shared rate limiting, object storage for certificates

## Security Configuration

**Container Security:**
- Non-root user execution
- Minimal base image (slim Python)
- No unnecessary packages installed
- Read-only certificate mounts

**Network Security:**
- Internal API communication (no external exposure)
- SSL/TLS termination at load balancer
- CORS configured for allowed origins
- Security headers injected by middleware

**Secret Management:**
- Environment variables for secrets
- No secrets in container images
- Secrets stored in secure vault (production)
- API keys stored in database (encrypted at rest)

## Current Implementation Status

All deployment components are implemented and production-ready:

- Multi-stage Docker build
- Gunicorn with Uvicorn workers
- Health checks and monitoring
- Database migrations via Alembic
- Certificate management
- Logging configuration
- Container security hardening

Future considerations (not currently implemented):

- Kubernetes deployment manifests
- Helm charts for package management
- CI/CD pipeline integration
- Automated database backups
- Multi-region deployment
- Shared rate limiting (Redis)
- Object storage for certificates

