# classic-models-api Helm chart

Deploys Classic Models API (Django/DRF) and its MySQL dependency as a single
Helm release, on an OpenShift cluster using the default `restricted-v2` SCC
(no root privileges, UID/GID assigned dynamically by the cluster). Supersedes
the plain manifests under `k8s/`, kept there as a reference/fallback.

## What's in the chart

- API: Secret, ConfigMap, Deployment (gunicorn, 2 replicas by default),
  Service, Route, a `pre-install`/`pre-upgrade` hook Job that runs
  `manage.py migrate` exactly once before any replica starts (avoids multiple
  pods racing to apply migrations concurrently).
- MySQL: Secret, PVC (kept across `helm uninstall`, see
  `helm.sh/resource-policy: keep`), init-SQL ConfigMap (loads
  `files/01-init.sql` via a small `.sh` loader script — the `rhel8/mysql-80`
  image only auto-runs `*.sh` files, not raw `.sql`), Deployment, headless
  Service.
- NetworkPolicy restricting MySQL ingress to the API pods only.
- Secrets (`SECRET_KEY`, `API_KEY`, MySQL passwords) are auto-generated on
  first install and preserved across `helm upgrade` (see
  `templates/_helpers.tpl`, function `classic-models-api.secretValue`) —
  no manual secret creation needed, unlike the plain-manifests flow.

## Prerequisites — IMPORTANT: do not use `--create-namespace`

The chart intentionally does **not** manage the Namespace resource. Do not
use `helm install --create-namespace` with this chart. Always create the
namespace yourself first, as a separate step.

This chart also does not build the application image — build/push it before
installing.

Full sequence (OpenShift, internal ImageStream — no external registry
credentials needed):

```bash
oc create namespace classic-models
oc create imagestream classic-models-api -n classic-models
oc new-build --name=classic-models-api --strategy=docker --binary -n classic-models
oc start-build classic-models-api --from-dir=. --follow -n classic-models

helm install classic-models-api helm/classic-models-api -n classic-models
```

If you'd rather push to an external registry (portable to any Kubernetes
distribution, not just OpenShift), use the repo root `Makefile` instead of
the OpenShift binary build, then point `api.image.repository`/`api.image.tag`
at that image:

```bash
oc create namespace classic-models   # or `kubectl create namespace` on vanilla K8s
make push REGISTRY=ghcr.io/your-org IMAGE_NAME=classic-models-api
helm install classic-models-api helm/classic-models-api -n classic-models \
  --set api.image.repository=ghcr.io/your-org/classic-models-api \
  --set api.image.tag=v4.7.0 \
  --set api.image.pullPolicy=IfNotPresent
```

See `values-example.yaml` for a fuller example (custom Route host, storage
class, pinned secrets) you can copy and adapt with `-f my-values.yaml`.

## Upgrading

```bash
helm upgrade classic-models-api helm/classic-models-api -n classic-models
```

Migrations re-run automatically as part of the upgrade (the `pre-upgrade`
hook), before the new Deployment revision rolls out.

## Uninstalling

```bash
helm uninstall classic-models-api -n classic-models
```

Note: resources annotated as Helm hooks without a `hook-delete-policy` (the
Secrets, ConfigMaps and the MySQL Deployment/Service/PVC — ordered this way
on purpose so they exist before the migration hook Job runs) are **not**
deleted by `helm uninstall`. Clean them up manually if you want a fully empty
namespace:

```bash
oc delete deployment,service,configmap,secret,pvc -n classic-models \
  -l app.kubernetes.io/part-of=classic-models-api
```

Do this deliberately — it also deletes the MySQL PVC and its data.

## Application notes

- JWT defaults to HS256 (signed with `SECRET_KEY`) unless
  `secrets.jwtPrivateKeyPem`/`secrets.jwtPublicKeyPem` are set, in which case
  RS256 + JWKS kick in automatically (see `docs/APIC_DATAPOWER_JWT.md` at the
  repo root for the API-gateway integration this supports).
- No demo user is created automatically — that behavior was removed from
  `scripts/start.sh`.
- Health probes hit `/classic-models/health/`, which checks a real DB
  connection rather than relying on a public business endpoint as an
  availability proxy.
