# Microservices Deployment Platform with Full Observability

A production-grade microservices platform deployed on AWS EKS with CI/CD, monitoring, and observability.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Container Orchestration | Kubernetes (AWS EKS) |
| Microservices | Python Flask |
| CI/CD | GitHub Actions |
| Container Registry | Amazon ECR |
| Monitoring | Prometheus + Grafana |
| Alerting | AlertManager |

## Services

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8080 | Routes requests, metrics collection |
| Auth Service | 8081 | JWT authentication, user management |
| Order Service | 8082 | Order CRUD, payment integration |
| Payment Service | 8083 | Payment processing |
| Notification Service | 8084 | Email/SMS/Push notifications |

## API Endpoints

### Auth
- POST /api/v1/auth/register - Register user
- POST /api/v1/auth/login - Login (returns JWT)
- GET /api/v1/auth/validate - Validate token

### Orders
- GET /api/v1/orders - List orders
- POST /api/v1/orders - Create order
- GET /api/v1/orders/:id - Get order

### Payments
- POST /api/v1/payments - Process payment
- GET /api/v1/payments/:id - Get payment

### Notifications
- POST /api/v1/notifications - Send notification

### Observability
- GET /health - Liveness probe
- GET /ready - Readiness probe
- GET /metrics - Prometheus metrics

## Monitoring

Access Grafana via port-forward on port 3000.
Login: admin / [REDACTED:PASSWORD]

## CI/CD Pipeline

The GitHub Actions pipeline:
1. Lint and Test - Flake8 linting + health check tests
2. Build and Push - Docker build + push to ECR
3. Deploy - Rolling update on EKS

## Author
Avipsha Lala - Cloud Support Engineer at AWS
