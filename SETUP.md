# Cloud-Based Stock Price Prediction System
## Complete Setup Guide — All Commands

---

## Prerequisites

Install these before starting:
- Docker Desktop
- kubectl
- AWS CLI
- eksctl

---

## Step 1 — Configure AWS CLI

```powershell
aws configure
```
Enter when prompted:
- AWS Access Key ID
- AWS Secret Access Key
- Default region: ap-south-1
- Default output format: json

Verify:
```powershell
aws sts get-caller-identity
```

---

## Step 2 — Set Environment Variables

Run these one at a time in every new PowerShell session:

```powershell
$AWS_ACCOUNT = aws sts get-caller-identity --query Account --output text
```
```powershell
$AWS_REGION = "ap-south-1"
```
```powershell
$ECR = "$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com"
```
```powershell
echo $ECR
```

Or hardcode directly (replace with your account ID):
```powershell
$ECR = "193926907633.dkr.ecr.ap-south-1.amazonaws.com"
```

---

## Step 3 — Create EKS Cluster

```powershell
eksctl create cluster `
  --name stock-cluster `
  --region ap-south-1 `
  --nodegroup-name workers `
  --node-type t3.medium `
  --nodes 2 `
  --nodes-min 2 `
  --nodes-max 8 `
  --managed
```

Verify cluster is ready:
```powershell
kubectl get nodes
```

---

## Step 4 — Create ECR Repositories

```powershell
aws ecr create-repository --repository-name stock-prediction-api --region ap-south-1
```
```powershell
aws ecr create-repository --repository-name stock-prediction-ui --region ap-south-1
```

---

## Step 5 — Login Docker to ECR

Run this every 12 hours (ECR tokens expire):
```powershell
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin $ECR
```

---

## Step 6 — Build and Push Docker Images

```powershell
docker build --no-cache -t $ECR/stock-prediction-api:v1 .
```
```powershell
docker push $ECR/stock-prediction-api:v1
```
```powershell
docker build -f Dockerfile.ui -t $ECR/stock-prediction-ui:latest .
```
```powershell
docker push $ECR/stock-prediction-ui:latest
```

---

## Step 7 — Create Kubernetes Namespace

```powershell
kubectl apply -f k8s/base/namespace.yaml
```

---

## Step 8 — Create ConfigMaps and Secrets

```powershell
kubectl create configmap stock-data-configmap `
  --namespace stock-prediction `
  --from-file=stock_data.csv=app/stock_data.csv
```
```powershell
kubectl create secret generic stock-prediction-secrets `
  --namespace stock-prediction `
  --from-literal=alphavantage-api-key=demo
```
```powershell
kubectl create secret generic grafana-secrets `
  --namespace stock-prediction `
  --from-literal=admin-password=admin123
```

---

## Step 9 — Deploy the Application

```powershell
kubectl apply -f k8s/base/deployment.yaml
```
```powershell
kubectl apply -f k8s/base/hpa-ingress.yaml
```

---

## Step 10 — Deploy Monitoring Stack (Prometheus + Grafana)

```powershell
kubectl apply -f k8s/monitoring/monitoring-stack.yaml
```

Fix Prometheus scrape config:
```powershell
kubectl apply -f prometheus/prometheus-config.yaml
```

---

## Step 11 — Verify All Pods Are Running

```powershell
kubectl get pods -n stock-prediction
```

Expected output:
```
grafana-xxx                  1/1   Running
prometheus-xxx               1/1   Running
stock-prediction-api-xxx     1/1   Running
stock-prediction-api-xxx     1/1   Running
stock-prediction-ui-xxx      1/1   Running
```

---

## Step 12 — Access Services (Port Forwarding)

Open 4 separate PowerShell terminals and run one command in each:

**Terminal 1 — API:**
```powershell
kubectl port-forward svc/stock-prediction-api-service 8000:8000 -n stock-prediction
```

**Terminal 2 — Streamlit UI:**
```powershell
kubectl port-forward svc/stock-prediction-ui-service 8054:8054 -n stock-prediction
```

**Terminal 3 — Prometheus:**
```powershell
kubectl port-forward svc/prometheus-service 9090:9090 -n stock-prediction
```

**Terminal 4 — Grafana:**
```powershell
kubectl port-forward svc/grafana-service 3001:3000 -n stock-prediction
```

---

## Step 13 — URLs

| Service        | URL                        | Credentials         |
|----------------|----------------------------|---------------------|
| Streamlit UI   | http://localhost:8054       | —                   |
| API Docs       | http://localhost:8000/docs  | —                   |
| Prometheus     | http://localhost:9090       | —                   |
| Grafana        | http://localhost:3001       | admin / admin123    |

---

## Step 14 — Set Up Grafana Dashboard

1. Open http://localhost:3001 → login: admin / admin123
2. Go to **Connections → Data Sources → Add data source**
3. Select **Prometheus**
4. Set URL to: `http://prometheus-service:9090`
5. Click **Save & Test**
6. Go to **Dashboards → Import**
7. Click **Upload dashboard JSON file**
8. Upload `grafana/dashboards/stock-prediction.json`
9. Select your Prometheus data source → click **Import**

---

## Step 15 — Test the API

```powershell
curl http://localhost:8000/health
```
```powershell
curl http://localhost:8000/predict/AAPL
```
```powershell
curl http://localhost:8000/predict/MSFT
```
```powershell
curl http://localhost:8000/predict/GOOG
```
```powershell
curl http://localhost:8000/predict/AMZN
```

---

## Redeployment — After Code Changes

Every time you change code:

```powershell
# Re-login to ECR (if token expired)
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin $ECR
```
```powershell
# Build with new version tag (increment v2, v3 etc — never reuse latest)
docker build --no-cache -t $ECR/stock-prediction-api:v2 .
```
```powershell
docker push $ECR/stock-prediction-api:v2
```
```powershell
# Update running deployment
kubectl set image deployment/stock-prediction-api api=$ECR/stock-prediction-api:v2 -n stock-prediction
```
```powershell
# Watch rollout
kubectl rollout status deployment/stock-prediction-api -n stock-prediction
```

---

## Debugging Commands

```powershell
# Check pod status
kubectl get pods -n stock-prediction

# View crash logs
kubectl logs -n stock-prediction <pod-name>

# View previous crash logs
kubectl logs -n stock-prediction <pod-name> --previous

# Describe pod (shows events and errors)
kubectl describe pod <pod-name> -n stock-prediction

# Check what files are inside the container
docker run --rm $ECR/stock-prediction-api:latest ls /app

# Check all services
kubectl get svc -n stock-prediction

# Check HPA (auto-scaling status)
kubectl get hpa -n stock-prediction

# Force restart a deployment
kubectl rollout restart deployment stock-prediction-api -n stock-prediction

# Check configmaps
kubectl get configmap -n stock-prediction

# Clear model cache
curl http://localhost:8000/cache/clear
```

---

## Tear Down (Delete Everything)

```powershell
# Delete all Kubernetes resources
kubectl delete namespace stock-prediction
```
```powershell
# Delete EKS cluster (stops AWS charges)
eksctl delete cluster --name stock-cluster --region ap-south-1
```
```powershell
# Delete ECR repositories
aws ecr delete-repository --repository-name stock-prediction-api --region ap-south-1 --force
aws ecr delete-repository --repository-name stock-prediction-ui --region ap-south-1 --force
```
