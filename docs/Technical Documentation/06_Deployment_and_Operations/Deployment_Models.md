# Deployment Models

## Deployment Options

The system supports multiple deployment models depending on scale and requirements.

## Single Container Deployment

**Use Case:** Development, small-scale production

**Components:**
- Single backend container
- External PostgreSQL database
- Frontend served as static files

**Configuration:**
- Docker Compose for local development
- Single container for small deployments
- Environment variables for configuration
- Volume mounts for certificates and logs

**Limitations:**
- No horizontal scaling
- Single point of failure
- Limited capacity

## Multi-Container Deployment

**Use Case:** Production deployments

**Components:**
- Multiple backend containers (load balanced)
- External PostgreSQL database (managed or self-hosted)
- Frontend served via CDN or web server
- Load balancer for request distribution

**Configuration:**
- Container orchestration (Kubernetes, ECS, Docker Swarm)
- Load balancer configuration
- Database connection pooling
- Shared certificate storage (object storage or shared volume)

**Scaling:**
- Horizontal scaling via container replication
- Load balancer distributes requests
- Database connection pooling handles multiple instances
- Rate limiting per instance (not shared)

## Container Configuration

### Backend Container

**Base Image:** `python:3.11-slim`

**Application Server:**
- Gunicorn with Uvicorn workers
- Worker count: `CPU_COUNT * 2 + 1`
- Preload app: Enabled
- Graceful timeout: 30 seconds

**Health Checks:**
- HTTP GET `/api/v1/health`
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3

**Resource Limits:**
- Memory: Configurable (default: 512MB)
- CPU: Configurable (default: 1 core)
- Disk: For logs and certificates

### Database

**PostgreSQL:**
- Managed service (recommended)
- Self-hosted (optional)
- Connection pooling required
- SSL/TLS connections required

**Configuration:**
- Connection string via `DATABASE_URL`
- Connection pool size: 10-20 connections
- SSL mode: require
- Backup and replication configured

## Environment Configuration

### Development

**Configuration:**
- `ENVIRONMENT_NAME=development`
- `DEBUG=true`
- `ENABLE_DOCS=true`
- `ZATCA_ENV=SANDBOX`
- SQLite database (optional)

**Deployment:**
- Local Docker Compose
- Direct Python execution
- Hot reload enabled
- Development certificates

### Production

**Configuration:**
- `ENVIRONMENT_NAME=production`
- `DEBUG=false`
- `ENABLE_DOCS=false`
- `ZATCA_ENV=PRODUCTION`
- PostgreSQL database (required)

**Deployment:**
- Container orchestration
- Load balancer
- SSL/TLS termination
- Production certificates
- Monitoring and alerting

## Scaling Considerations

### Vertical Scaling

**Method:**
- Increase container resources (CPU, memory)
- Increase worker count
- Increase database resources

**Limitations:**
- Single instance capacity
- No redundancy
- Downtime during scaling

### Horizontal Scaling

**Method:**
- Multiple container instances
- Load balancer distribution
- Shared database
- Shared certificate storage

**Challenges:**
- Rate limiting (in-memory, not shared)
- Certificate storage (filesystem, not shared)
- Session state (stateless design)

**Solutions:**
- Redis for shared rate limiting (future)
- Object storage for certificates (future)
- Stateless application design (current)

## Current Implementation Status

All deployment components are implemented:

- Single container deployment
- Docker Compose configuration
- Health checks
- Environment configuration
- Database migrations

Future considerations (not currently implemented):

- Kubernetes deployment manifests
- Helm charts
- Multi-container orchestration
- Shared rate limiting (Redis)
- Object storage for certificates
- Automated scaling
- Blue-green deployments
- Canary deployments

