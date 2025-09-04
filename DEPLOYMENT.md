# Deployment Guide 🚀

This guide covers various deployment options for the HN GitHub Agents application, from local development to production cloud deployment.

## 📋 Table of Contents

- [Local Development](#-local-development)
- [Docker Deployment](#-docker-deployment)
- [Cloud Deployment](#-cloud-deployment)
- [Production Considerations](#-production-considerations)
- [Monitoring & Observability](#-monitoring--observability)
- [Security](#-security)

## 🛠️ Local Development

### Quick Start
```bash
# 1. Setup environment
python -m venv venv
source venv/bin/activate
pip install -e .

# 2. Configure environment
cp env.example .env
# Edit .env with your API keys

# 3. Start MCP servers
./scripts/setup_mcp_servers.sh setup

# 4. Run application
python -m app.main
```

### Development with Hot Reload
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🐳 Docker Deployment

### Single Container
```bash
# Build the image
docker build -t hn-github-agents:latest .

# Run the container
docker run -d \
  --name hn-github-agents \
  -p 8000:8000 \
  -e OPENAI_API_KEY="your_key" \
  -e GITHUB_TOKEN="your_token" \
  hn-github-agents:latest
```

### Docker Compose (Recommended)
```bash
# Start all services
docker-compose up -d

# Scale the main application
docker-compose up -d --scale hn-github-agents=3

# View logs
docker-compose logs -f hn-github-agents

# Stop services
docker-compose down
```

### Custom Docker Compose for Production
```yaml
version: '3.8'

services:
  hn-github-agents:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - WORKERS=4
    depends_on:
      - redis
      - brave-search-mcp
      - github-mcp
      - hackernews-mcp
      - filesystem-mcp
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - hn-github-agents
    restart: unless-stopped
```

## ☁️ Cloud Deployment

### AWS Deployment

#### Using AWS ECS Fargate
```yaml
# ecs-task-definition.json
{
  "family": "hn-github-agents",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "hn-github-agents",
      "image": "your-account.dkr.ecr.region.amazonaws.com/hn-github-agents:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:openai-key"
        },
        {
          "name": "GITHUB_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:github-token"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/hn-github-agents",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

#### Deploy to ECS
```bash
# Build and push to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-west-2.amazonaws.com

docker build -t hn-github-agents .
docker tag hn-github-agents:latest 123456789012.dkr.ecr.us-west-2.amazonaws.com/hn-github-agents:latest
docker push 123456789012.dkr.ecr.us-west-2.amazonaws.com/hn-github-agents:latest

# Register task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create or update service
aws ecs create-service \
  --cluster hn-github-agents-cluster \
  --service-name hn-github-agents \
  --task-definition hn-github-agents:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-abcdef],assignPublicIp=ENABLED}"
```

### Google Cloud Platform

#### Using Cloud Run
```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: hn-github-agents
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        autoscaling.knative.dev/minScale: "1"
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/memory: "2Gi"
        run.googleapis.com/cpu: "1000m"
    spec:
      containers:
      - image: gcr.io/your-project/hn-github-agents:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-key
              key: api-key
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: github-token
              key: token
        resources:
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
```

#### Deploy to Cloud Run
```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/your-project/hn-github-agents

# Deploy to Cloud Run
gcloud run deploy hn-github-agents \
  --image gcr.io/your-project/hn-github-agents:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production \
  --memory 2Gi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10
```

### Azure Container Instances

```bash
# Create resource group
az group create --name hn-github-agents-rg --location eastus

# Deploy container
az container create \
  --resource-group hn-github-agents-rg \
  --name hn-github-agents \
  --image your-registry/hn-github-agents:latest \
  --ports 8000 \
  --dns-name-label hn-github-agents-demo \
  --environment-variables ENVIRONMENT=production \
  --secure-environment-variables OPENAI_API_KEY=your-key GITHUB_TOKEN=your-token \
  --cpu 2 \
  --memory 4
```

### Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hn-github-agents
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hn-github-agents
  template:
    metadata:
      labels:
        app: hn-github-agents
    spec:
      containers:
      - name: hn-github-agents
        image: your-registry/hn-github-agents:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: openai-key
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: github-token
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: hn-github-agents-service
spec:
  selector:
    app: hn-github-agents
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer

---
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
type: Opaque
data:
  openai-key: <base64-encoded-key>
  github-token: <base64-encoded-token>
```

## 🏭 Production Considerations

### Environment Variables
```bash
# Production environment variables
ENVIRONMENT=production
LOG_LEVEL=INFO
WORKERS=4
HOST=0.0.0.0
PORT=8000

# Security
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...

# Database (if using)
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://redis:6379/0

# Monitoring
SENTRY_DSN=https://...
DATADOG_API_KEY=...
```

### Health Checks
The application provides comprehensive health checks:

```bash
# Application health
curl http://localhost:8000/health

# Agent status
curl http://localhost:8000/api/v1/agents/status

# MCP server status
curl http://localhost:8000/api/v1/mcp/status
```

### Load Balancing with Nginx

```nginx
# nginx.conf
upstream hn_github_agents {
    server hn-github-agents-1:8000;
    server hn-github-agents-2:8000;
    server hn-github-agents-3:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://hn_github_agents;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Health check exclusion
        location /health {
            access_log off;
            proxy_pass http://hn_github_agents;
        }
    }
}
```

### Scaling Configuration

```yaml
# docker-compose.override.yml for production
version: '3.8'

services:
  hn-github-agents:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s
    environment:
      - WORKERS=4
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
```

## 📊 Monitoring & Observability

### Application Metrics
The application exposes metrics for monitoring:

```python
# Custom metrics can be added
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')
```

### Logging Configuration
```python
# Production logging setup
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

### Prometheus Integration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'hn-github-agents'
    static_configs:
      - targets: ['hn-github-agents:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

## 🔒 Security

### API Security
```python
# Add API key authentication
from fastapi import Security, HTTPException, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_api_key(token: str = Security(security)):
    if token.credentials != "your-api-key":
        raise HTTPException(status_code=403, detail="Invalid API key")
    return token
```

### Environment Security
```bash
# Use secrets management
export OPENAI_API_KEY=$(aws secretsmanager get-secret-value --secret-id openai-key --query SecretString --output text)
export GITHUB_TOKEN=$(aws secretsmanager get-secret-value --secret-id github-token --query SecretString --output text)
```

### Container Security
```dockerfile
# Security-hardened Dockerfile
FROM python:3.11-slim

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser

# Set security-focused environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install security updates
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
WORKDIR /app
COPY pyproject.toml ./
RUN pip install -e .

# Copy application
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Network Security
```yaml
# docker-compose with network isolation
version: '3.8'

services:
  hn-github-agents:
    networks:
      - frontend
      - backend
    
  mcp-servers:
    networks:
      - backend

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true
```

## 🚀 CI/CD Pipeline

### GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v3
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest
      - run: ruff check app/
      - run: mypy app/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and push Docker image
        run: |
          docker build -t ${{ secrets.REGISTRY }}/hn-github-agents:${{ github.sha }} .
          docker push ${{ secrets.REGISTRY }}/hn-github-agents:${{ github.sha }}
      
      - name: Deploy to production
        run: |
          # Deploy to your chosen platform
          echo "Deploying to production..."
```

This comprehensive deployment guide covers everything from local development to production cloud deployment. Choose the deployment method that best fits your infrastructure and requirements.
