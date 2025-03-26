apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - namespace.yaml
  - redis-deployment.yaml
  - redis-service.yaml
  - api-deployment.yaml
  - api-service.yaml
  - api-hpa.yaml
  - api-configmap.yaml


apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: mlops-staging

resources:
  - ../../base
  - staging-ingress.yaml

patchesStrategicMerge:
  - api-deployment-patch.yaml
  - api-hpa-patch.yaml
  - api-configmap-patch.yaml
  
secretGenerator:
  - name: mlops-secrets
    envs:
      - secrets.env
    type: Opaque

images:
  - name: mlops-api
    newName: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mlops-api
    newTag: latest


apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: mlops-staging

resources:
  - ../../base
  - staging-ingress.yaml

patchesStrategicMerge:
  - api-deployment-patch.yaml
  - api-hpa-patch.yaml
  - api-configmap-patch.yaml
  
secretGenerator:
  - name: mlops-secrets
    envs:
      - secrets.env
    type: Opaque

images:
  - name: mlops-api
    newName: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mlops-api
    newTag: latest

apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: mlops-production

resources:
  - ../../base
  - production-ingress.yaml
  - prometheus-servicemonitor.yaml

patchesStrategicMerge:
  - api-deployment-patch.yaml
  - api-hpa-patch.yaml
  - api-configmap-patch.yaml
  
secretGenerator:
  - name: mlops-secrets
    envs:
      - secrets.env
    type: Opaque

images:
  - name: mlops-api
    newName: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mlops-api
    newTag: latest