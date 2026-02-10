#!/bin/bash
set -e

# Variables
AWS_REGION="eu-west-2"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_TAG="v1"

echo "🚀 Deploying Microservices to EKS..."

# Update kubeconfig
aws eks update-kubeconfig --region ${AWS_REGION} --name test1

# Create namespace
echo "Creating namespace..."
kubectl apply -f kubernetes/base/namespace.yaml

# Create ConfigMap and Secrets
echo "Creating ConfigMap and Secrets..."
kubectl apply -f kubernetes/base/configmap.yaml
kubectl apply -f kubernetes/base/secrets.yaml

# Create ServiceAccount
echo "Creating ServiceAccount..."
kubectl apply -f kubernetes/base/serviceaccount.yaml

# Deploy services with actual image URLs
echo "Deploying services..."

for service in api-gateway auth-service order-service payment-service notification-service; do
    echo "Deploying ${service}..."
    SERVICE_UPPER=$(echo ${service} | tr '-' '_' | tr '[:lower:]' '[:upper:]')
    
    sed "s|${SERVICE_UPPER}_IMAGE|${REGISTRY}/microservices/${service}:${IMAGE_TAG}|g" \
        kubernetes/base/${service}.yaml | kubectl apply -f -
done

# Wait for deployments
echo "Waiting for deployments to be ready..."
kubectl -n microservices wait --for=condition=available --timeout=300s deployment --all

# Show status
echo ""
echo "✅ Deployment Complete!"
echo ""
kubectl -n microservices get pods
kubectl -n microservices get svc

