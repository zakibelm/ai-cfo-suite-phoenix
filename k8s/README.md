# Kubernetes Deployment Guide

Deploy AI CFO Suite Phoenix on Kubernetes for production-grade scalability and high availability.

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured
- Helm 3+ installed
- Storage class `fast-ssd` available (or modify manifests)
- Ingress controller (nginx-ingress)
- cert-manager (for HTTPS certificates)

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. Configure Secrets

```bash
# Copy and edit secrets template
cp k8s/secrets.yaml.example k8s/secrets.yaml
nano k8s/secrets.yaml

# Generate secure keys
python3 -c "import secrets; print('SECRET_KEY:', secrets.token_urlsafe(32))"
python3 -c "import secrets; print('ENCRYPTION_KEY:', secrets.token_urlsafe(24))"

# Apply secrets
kubectl apply -f k8s/secrets.yaml
```

### 3. Deploy Infrastructure

Deploy stateful services (PostgreSQL, Redis, Qdrant):

```bash
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/redis-statefulset.yaml
kubectl apply -f k8s/qdrant-statefulset.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n aicfo --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n aicfo --timeout=300s
kubectl wait --for=condition=ready pod -l app=qdrant -n aicfo --timeout=300s
```

### 4. Deploy Applications

```bash
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

# Wait for deployments
kubectl wait --for=condition=available deployment/backend -n aicfo --timeout=300s
kubectl wait --for=condition=available deployment/frontend -n aicfo --timeout=300s
```

### 5. Configure Ingress

```bash
# Edit ingress.yaml to set your domain
nano k8s/ingress.yaml

# Apply ingress
kubectl apply -f k8s/ingress.yaml
```

### 6. Verify Deployment

```bash
# Check all resources
kubectl get all -n aicfo

# Check pods
kubectl get pods -n aicfo -o wide

# Check services
kubectl get svc -n aicfo

# Check ingress
kubectl get ingress -n aicfo

# Check HPA
kubectl get hpa -n aicfo

# View logs
kubectl logs -f deployment/backend -n aicfo
kubectl logs -f deployment/frontend -n aicfo
```

## Scaling

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment backend --replicas=5 -n aicfo

# Scale frontend
kubectl scale deployment frontend --replicas=3 -n aicfo
```

### Horizontal Pod Autoscaling (HPA)

HPA is automatically configured:

- **Backend**: 3-10 replicas (CPU: 70%, Memory: 80%)
- **Frontend**: 2-5 replicas (CPU: 70%, Memory: 80%)

View HPA status:

```bash
kubectl get hpa -n aicfo
kubectl describe hpa backend-hpa -n aicfo
```

## Monitoring

### Metrics

```bash
# View backend metrics
kubectl port-forward -n aicfo deployment/backend 8000:8000
curl http://localhost:8000/api/v1/monitoring/metrics

# View pod metrics
kubectl top pods -n aicfo
kubectl top nodes
```

### Logs

```bash
# Stream logs
kubectl logs -f deployment/backend -n aicfo --tail=100
kubectl logs -f deployment/frontend -n aicfo --tail=100

# Get logs from all pods
kubectl logs -l app=backend -n aicfo --tail=50

# Previous container logs (after crash)
kubectl logs deployment/backend -n aicfo --previous
```

## Updates and Rollouts

### Rolling Update

```bash
# Update backend image
kubectl set image deployment/backend backend=zakibelm/ai-cfo-backend:v3.1.0 -n aicfo

# Update frontend image
kubectl set image deployment/frontend frontend=zakibelm/ai-cfo-frontend:v3.1.0 -n aicfo

# Watch rollout status
kubectl rollout status deployment/backend -n aicfo
kubectl rollout status deployment/frontend -n aicfo
```

### Rollback

```bash
# View rollout history
kubectl rollout history deployment/backend -n aicfo

# Rollback to previous version
kubectl rollout undo deployment/backend -n aicfo

# Rollback to specific revision
kubectl rollout undo deployment/backend --to-revision=2 -n aicfo
```

## Database Migrations

```bash
# Run migrations in a pod
kubectl exec -it deployment/backend -n aicfo -- alembic upgrade head

# Or create a Job
kubectl create job --from=deployment/backend db-migrate -n aicfo -- alembic upgrade head
```

## Backup and Restore

### PostgreSQL Backup

```bash
# Create backup
kubectl exec -it postgres-0 -n aicfo -- pg_dump -U aicfo aicfo_db > backup.sql

# Restore backup
cat backup.sql | kubectl exec -i postgres-0 -n aicfo -- psql -U aicfo -d aicfo_db
```

### Qdrant Backup

```bash
# Create snapshot
kubectl exec -it qdrant-0 -n aicfo -- curl -X POST http://localhost:6333/snapshots

# Copy snapshot
kubectl cp aicfo/qdrant-0:/qdrant/storage/snapshots/snapshot.tar ./qdrant-backup.tar
```

## Troubleshooting

### Pods not starting

```bash
# Describe pod
kubectl describe pod <pod-name> -n aicfo

# Check events
kubectl get events -n aicfo --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n aicfo
```

### Service not reachable

```bash
# Check service endpoints
kubectl get endpoints -n aicfo

# Test service internally
kubectl run curl --rm -it --image=curlimages/curl -- sh
curl http://backend.aicfo:8000/api/v1/monitoring/health
```

### PVC issues

```bash
# Check PVCs
kubectl get pvc -n aicfo

# Describe PVC
kubectl describe pvc postgres-storage-postgres-0 -n aicfo

# Check storage class
kubectl get storageclass
```

### Resource issues

```bash
# Check resource usage
kubectl top pods -n aicfo
kubectl top nodes

# Check resource limits
kubectl describe deployment backend -n aicfo | grep -A 5 Limits
```

## Performance Tuning

### Backend Optimization

```yaml
# Increase replicas and resources
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### Database Optimization

```yaml
# Increase PostgreSQL resources
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### Redis Optimization

```yaml
# Increase Redis memory
command:
- redis-server
- --maxmemory 4gb
- --maxmemory-policy allkeys-lru
```

## Security

### Network Policies

Create network policies to restrict traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-network-policy
  namespace: aicfo
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx-ingress
    ports:
    - protocol: TCP
      port: 8000
```

### Pod Security

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  readOnlyRootFilesystem: true
```

## Clean Up

```bash
# Delete all resources
kubectl delete namespace aicfo

# Or delete individually
kubectl delete -f k8s/
```

## Production Checklist

- [ ] Configure secrets properly
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure backup strategy
- [ ] Set up logging (ELK/Loki)
- [ ] Configure network policies
- [ ] Set resource requests/limits
- [ ] Configure HTTPS with cert-manager
- [ ] Set up CI/CD pipeline
- [ ] Configure alerting
- [ ] Test disaster recovery
- [ ] Document runbooks
- [ ] Set up node autoscaling

## Support

For issues or questions, refer to:
- Main documentation: `/docs`
- GitHub issues: https://github.com/zakibelm/ai-cfo-suite-phoenix/issues
