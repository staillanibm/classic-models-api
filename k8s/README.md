# Kubernetes / OpenShift Deployment (SCC `restricted-v2`)

Manifests to deploy Classic Models API and its MySQL dependency on an
OpenShift cluster using the default `restricted-v2` SCC (no root privileges,
UID/GID assigned dynamically by the cluster).

## Structure

- `k8s/` : namespace, ConfigMap/Secret, Deployment, Service, Route, NetworkPolicy for the API.
- `k8s/mysql/` : init SQL ConfigMap, Secret, PVC, Deployment, headless Service for MySQL.

## Prerequisites before deploying

1. **Secrets to fill in** (never commit real values):
   - `k8s/01-secret.yaml`: `SECRET_KEY`, `API_KEY`, `MYSQL_PASSWORD`, `DATABASE_URL`,
     and optionally `JWT_PRIVATE_KEY_PEM`/`JWT_PUBLIC_KEY_PEM` (otherwise falls back to
     HS256 via `SECRET_KEY`).
   - `k8s/mysql/01-secret.yaml`: `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD` (must match
     the one in the application secret above).

   Prefer generating these secrets out of band, e.g.:
   ```bash
   oc create secret generic mysql-credentials -n classic-models \
     --from-literal=MYSQL_ROOT_PASSWORD='...' \
     --from-literal=MYSQL_DATABASE='classicmodels' \
     --from-literal=MYSQL_USER='classicuser' \
     --from-literal=MYSQL_PASSWORD='...'

   oc create secret generic classic-models-api-secrets -n classic-models \
     --from-literal=SECRET_KEY='...' \
     --from-literal=API_KEY='...' \
     --from-literal=MYSQL_USER='classicuser' \
     --from-literal=MYSQL_PASSWORD='...' \
     --from-literal=DATABASE_URL='mysql://classicuser:...@mysql:3306/classicmodels'
   ```

2. **MySQL image**: `k8s/mysql/03-deployment.yaml` uses
   `registry.redhat.io/rhel8/mysql-80`, built to run under an arbitrary UID
   (group-root `g=u` permissions), unlike the Docker Hub `mysql:8.0` image
   (designed for root). A pull secret for `registry.redhat.io` is required
   (Red Hat subscription):
   ```bash
   oc create secret docker-registry redhat-registry-pull-secret \
     --docker-server=registry.redhat.io \
     --docker-username=<user> --docker-password=<password> \
     -n classic-models
   oc secrets link default redhat-registry-pull-secret --for=pull -n classic-models
   ```
   If an internal mirror is available, just adjust the `image:` field instead.

3. **API image**: `k8s/03-deployment.yaml` defaults to the cluster's internal
   ImageStream
   (`image-registry.openshift-image-registry.svc:5000/classic-models/classic-models-api:latest`),
   built via `oc new-build --strategy=docker --binary` +
   `oc start-build --from-dir=.`. Adjust if you use an external registry
   (ghcr.io, Quay...) instead.

## Deployment

```bash
oc apply -k k8s/mysql/
oc apply -f k8s/00-namespace.yaml -f k8s/01-secret.yaml -f k8s/02-configmap.yaml

# Migrations first, as a one-shot, before any API replica starts
# (avoids multiple pods racing to run `manage.py migrate` concurrently):
oc delete job classic-models-api-migrate -n classic-models --ignore-not-found
oc apply -f k8s/03a-migrate-job.yaml
oc wait --for=condition=complete job/classic-models-api-migrate -n classic-models --timeout=120s

oc apply -f k8s/03-deployment.yaml -f k8s/04-service.yaml -f k8s/05-route.yaml -f k8s/06-networkpolicy.yaml
```

The `03a-migrate-job.yaml` Job is not included in `kustomization.yaml`: it
must be deleted/reapplied by hand for every deployment that has new
migrations, rather than being silently recreated by `oc apply -k k8s/`.

> Note: this plain-manifests flow has been superseded by the Helm chart in
> `helm/classic-models-api/`, which wires the migration step as a proper
> `pre-install`/`pre-upgrade` hook instead of a manual step. Kept here as a
> reference/fallback.

## `restricted-v2` compatibility

- No `runAsUser`/`fsGroup` is pinned: OCP assigns them automatically per namespace.
- `runAsNonRoot: true`, `allowPrivilegeEscalation: false`,
  `capabilities.drop: [ALL]`, `seccompProfile: RuntimeDefault` on every container.
- `readOnlyRootFilesystem: true` on the API (with an `emptyDir` mounted on
  `/tmp` for temporary writes); MySQL keeps a writable root filesystem
  (required by the RHEL MySQL image) but no extra capability is granted.
- The MySQL PVC uses the cluster's default `storageClassName`; set it
  explicitly if your cluster requires it.

## Application notes

- The container starts via `gunicorn` (`scripts/start.sh`), with
  `DJANGO_SETTINGS_MODULE=config.settings.production` (see `k8s/02-configmap.yaml`).
  Migrations no longer run at pod startup — they're applied by the
  `k8s/03a-migrate-job.yaml` Job, to be run before any rollout.
- No more automatic `demo` user creation in production.
- API probes hit `/classic-models/health/` (`config/views.py`), which checks
  a real DB connection (`SELECT 1`) instead of relying on a public business
  endpoint as an availability proxy.
