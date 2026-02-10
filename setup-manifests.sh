#!/bin/bash

mkdir -p kubernetes/base

# Namespace
cat > kubernetes/base/namespace.yaml << 'EOF'
apiVersion: v1
kind: Namespace
metadata:
  name: microservices
  labels:
    name: microservices
EOF

# ConfigMap
cat > kubernetes/base/configmap.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: services-config
  namespace: microservices
data:
  AUTH_SERVICE_URL: "http://auth-service.microservices.svc.cluster.local"
  ORDER_SERVICE_URL: "http://order-service.microservices.svc.cluster.local"
  PAYMENT_SERVICE_URL: "http://payment-service.microservices.svc.cluster.local"
  NOTIFICATION_SERVICE_URL: "http://notification-service.microservices.svc.cluster.local"
  LOG_LEVEL: "INFO"
  XRAY_DAEMON_ADDRESS: "xray-daemon.microservices.svc.cluster.local:2000"
EOF

# Secrets
cat > kubernetes/base/secrets.yaml << 'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: services-secrets
  namespace: microservices
type: Opaque
stringData:
  JWT_SECRET_KEY: "your-super-secret-jwt-key-change-in-production"
EOF

# ServiceAccount
cat > kubernetes/base/serviceaccount.yaml << 'EOF'
apiVersion: v1
kind: ServiceAccount
metadata:
  name: microservices-sa
  namespace: microservices
EOF

echo "Created base manifests"
