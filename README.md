# lfi-service-2-app

The stateless worker for a local GitOps Kubernetes platform. FastAPI, Python 3.12.

**Companion to a build guide.** This is the reference version of what you build in
Section 3 of [local-full-infrastructure](https://github.com/mhonnczedz1/local-full-infrastructure).
Read the guide for why it is shaped this way; clone this only to compare against your own.

## What it does

Receives internal HTTP from `service-1` only, over cluster DNS. It is never reachable
from outside the cluster: there is no Ingress for it, and there should not be.

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Liveness. No readiness endpoint, deliberately: this service has no dependencies, so readiness would only duplicate liveness. |
| `POST /process` | Doubles its input and echoes its own service name. |

`/process` returning `"service": "service-2"` is what lets service-1's response prove
the internal DNS hop actually happened rather than being faked locally.

## The boundary this repo exists to hold

**No database access, by design.** That is the point of the two-service split, not an
unfinished feature. If you find yourself wanting to give this service a connection,
that is the signal you have drifted from the architecture.

Like service-1, it carries no Kubernetes manifests and no cluster credentials. CI builds
an image, pushes it to GHCR, and writes one tag into the
[GitOps repo](https://github.com/mhonnczedz1/lfi-infrastructure-gitops).

## Running the tests

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v && ruff check src tests
```

The business logic is a pure function kept separate from the route handler, so most of
the suite runs with no app, no client, and no I/O.

## CI

`test` runs lint and tests on every push and pull request. `build` publishes a
multi-arch image to GHCR, tagged with both a weekly build ordinal and the commit SHA,
and is skipped on pull requests. `promote` writes the build tag into the GitOps repo's
**dev** overlay. Nothing here ever writes to prod.
