# Microservices Deployment Platform with Full Observability

A production-grade microservices platform deployed on AWS EKS with CI/CD, monitoring, and observability.

## Live Dashboard

[Dashboard Screenshot](screenshots/dashboard.png)

---

## Architecture

                GitHub Actions (CI/CD)
                       |
                       v
                  Amazon ECR
                       |
                       v
+--------------------------------------------------+
|              EKS Cluster (test1)                  |
|                                                    |
|  Frontend --> API Gateway --> Auth Service          |
|                  |                                  |
|         Order Service  Payment Service              |
|                  |                                  |
|         Notification Service                       |
|                                                    |
|  Prometheus  |  Grafana  |  AlertManager            |
+--------------------------------------------------+

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Container Orchestration | Kubernetes (AWS EKS) |
| Microservices | Python Flask |
| Frontend | HTML/CSS/JS + Nginx |
| CI/CD | GitHub Actions |
| Container Registry | Amazon ECR |
| Monitoring | Prometheus + Grafana |
| Alerting | AlertManager |

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 80 | Web dashboard with API testing |
| API Gateway | 8080 | Request routing, metrics collection |
| Auth Service | 8081 | JWT authentication, user management |
| Order Service | 8082 | Order CRUD, payment integration |
| Payment Service | 8083 | Payment processing (95% success rate) |
| Notification Service | 8084 | Email/SMS/Push notifications |

## Screenshots

### Dashboard Overview
<!-- Paste your dashboard screenshot here -->

### API Testing
<!-- Paste your API testing screenshot here -->

### Grafana Monitoring
<!-- Paste your Grafana screenshot here -->

### Kubernetes Pods
<!-- Paste your kubectl get pods screenshot here -->

---

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

Prometheus + Grafana stack with custom dashboards tracking:
- Request rate per endpoint
- P99 latency
- Error rates
- Order and payment counts
- Pod CPU/Memory usage

## CI/CD Pipeline

GitHub Actions pipeline:
1. Lint and Test - Flake8 linting plus health check tests
2. Build and Push - Docker build plus push to ECR
3. Deploy - Rolling update on EKS

## Author
Avipsha Lala - Cloud Support Engineer at AWS
