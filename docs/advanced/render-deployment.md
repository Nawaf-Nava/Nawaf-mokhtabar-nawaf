# Render viewer deployment

This deployment runs only the Strix result viewer on Render. It does not
execute Strix scans in the Render web service.

## Why scans run elsewhere

Strix creates sandbox containers through the Docker SDK and configures
capabilities (`NET_ADMIN`, `NET_RAW`), devices, bind mounts, and exposed
ports. Render supports Docker images as the service build/runtime format, but
does not document a nested Docker daemon or privileged-container runtime
contract. The viewer must therefore not assume that `DOCKER_HOST`, a Docker
socket, privileged mode, or Docker-in-Docker is available. The unchanged
`containers/Dockerfile` is the scan sandbox image; `Dockerfile.render` builds
only the web viewer runtime.

Run the engine in a separate Docker-capable and isolated worker you control.
Restrict its inbound access, egress, CPU, memory, process count, disk use, and
target scope independently. Do not expose a Docker daemon to the public
internet. Configure the worker's own authorization/scope controls; the viewer
does not accept scan instructions or targets.

## Render service

The root `render.yaml` defines one Docker Web Service with:

- `Dockerfile.render` as its Dockerfile.
- One instance, because Render persistent disks are single-instance.
- A 10 GB persistent disk at `/data`.
- `STRIX_RUNS_DIR=/data/strix_runs` and HTTP health path `/health`.
- No scan engine, Docker daemon, LLM secret, or public worker service.

The startup manager checks hosted credentials and the mounted disk, then
executes `strix view --empty --host 0.0.0.0 --port "$PORT" --no-open` as PID 1.
The viewer's existing session-cookie checks still protect scan data and
mutations. HTTP Basic authentication is additionally required for public
viewer routes when configured; health probes bypass it. Use the Render HTTPS
endpoint. Render disks cause a short interruption during deploys and cannot
be horizontally scaled.

## Required environment variables

Set these in the Render service's environment settings as secrets:

| Name | Required | Notes |
| --- | --- | --- |
| `STRIX_VIEWER_USERNAME` | Yes | HTTP Basic authentication user. |
| `STRIX_VIEWER_PASSWORD` | Yes | At least 20 characters; use a generated secret. |
| `STRIX_WORKER_TOKEN` | Blueprint-generated | Render generates a base64-encoded 256-bit value. Copy it securely to the trusted worker; remove the variable to disable upload. |

The Blueprint sets `STRIX_RUNS_DIR`. Render supplies `PORT` (normally 10000);
leave it Render-managed. Do not set `LLM_API_KEY` on the viewer; the web
service does not scan. A scan worker needs its own model/provider credentials
and normal Strix settings in its own secret store.

## Publish completed results

On the isolated worker, use the same source revision (the helper is in
`scripts/upload_worker_run.py`) and set:

- `STRIX_VIEWER_URL` to the viewer's HTTPS origin, without a path.
- `STRIX_WORKER_TOKEN` to the viewer's worker token.
- `STRIX_RUNS_DIR` to the worker's local run directory, normally
  `strix_runs`.

After a scan of an explicitly authorized target completes, invoke
`python scripts/upload_worker_run.py <run-name>`. The helper accepts only a
terminal run record whose name matches, and uploads an allowlisted archive
using HTTPS and bearer authentication. The viewer applies the same checks,
rejects duplicate names and traversal/symlinks, and caps compressed and
uncompressed content. Stored artifacts are visible under the viewer's past
runs feature after the existing account verification gate.

No results are stored on Render until this separate, explicit upload occurs.
The worker is not provisioned or supervised by this Blueprint; Render's
external worker feature, another cloud service, or customer-controlled
Docker-capable host may be used, subject to security review and target
authorization. This result-upload integration is not a job queue and offers
no scan status, cancellation, retry, or execution API.

## Limits and checks

The viewer's `ThreadingHTTPServer` is suitable for the static SPA and file
reads, not as a high-throughput execution API. Run uploads are limited to 48
MiB compressed / 192 MiB unpacked and 1000 files, and currently include
run metadata, finding/report files, selected agent state files, telemetry
events, coverage, and SARIF. Other artifacts are intentionally excluded.

Validate deployment health at `GET /health`; it returns `{"status":"ok"}`.
Worker upload availability and actual Docker execution are not asserted by
that endpoint. The web service requires a paid Render plan for its persistent
disk. Size resources based on viewer traffic and retained output; size and
secure the engine worker separately. Render's plan-specific memory/CPU/build
limits are not inferred by this repository.