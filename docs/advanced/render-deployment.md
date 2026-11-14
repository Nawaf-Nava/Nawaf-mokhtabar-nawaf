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

- The root `Dockerfile` as its Dockerfile.
- One Free instance with no persistent disk.
- `STRIX_RUNS_DIR=/tmp/strix_runs` and HTTP health path `/health`.
- Temporary result storage inside the running container.
- No scan engine, Docker daemon, LLM secret, or public worker service.

The startup manager checks hosted credentials, creates the temporary results
directory, links it to the CLI's expected `/app/strix_runs` path, then
executes `strix view --empty --host 0.0.0.0 --port "$PORT" --no-open` as PID 1.
Results remain available only while the current container filesystem retains
them; a restart, redeploy, or instance replacement can erase them. Download
or export anything important before the service is recycled.
HTTP Basic authentication is disabled for this public demo. Anyone who can
reach the Render URL can view available run data. The server issues a
per-browser HttpOnly, Secure, SameSite=Strict cookie for API requests; this
is not an access-control barrier. Do not upload private or sensitive scan
results. Use the Render HTTPS endpoint.

## Required environment variables

Set these in the Render service's environment settings as secrets:

| Name | Required | Notes |
| --- | --- | --- |
| `STRIX_WORKER_TOKEN` | Blueprint-generated | Render generates a base64-encoded 256-bit value. Copy it securely to the trusted worker; remove the variable to disable upload. |

The Blueprint sets `STRIX_RUNS_DIR=/tmp/strix_runs` for temporary storage.
No viewer username or password is required; HTTP Basic authentication is
disabled. Render supplies `PORT` (normally 10000);
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

Uploaded results are stored in the viewer container's temporary filesystem.
They are not durable and can disappear when Render restarts or replaces the
instance.
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
that endpoint. The viewer Blueprint targets Render's Free plan and does not request a
persistent disk. This is suitable for temporary demonstrations, not durable
report retention. Size and secure the engine worker separately. Render's
plan-specific memory/CPU/build limits are not inferred by this repository.