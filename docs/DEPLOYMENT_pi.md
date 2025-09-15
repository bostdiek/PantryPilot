```markdown
# Deploying PantryPilot on a Raspberry Pi (local network / production-like)

This guide walks through deploying the PantryPilot production stack on a Raspberry Pi (ARM64/ARMv7) using Docker Engine and Docker Compose, with Nginx as the reverse proxy so the app is reachable from other devices on your LAN (phone, laptop, etc.).

Overview
- We'll run the stack using the provided `docker-compose.yml` + `docker-compose.prod.yml` (the repository's `Makefile` has shortcuts).
- Key concerns on Raspberry Pi:
  - Architectures: the Pi is ARM; many base images (Python/Node/nginx/postgres) have ARM builds, but third-party base layers (ghcr images like `astral-sh/uv`) may not be multi-arch. If a binary image is not available for ARM, build the image locally for ARM using Docker Buildx.
  - Resources: Pi has limited RAM and CPU. Use conservative `WORKERS` and enable swap if needed.

Prerequisites on your Raspberry Pi
- Raspberry Pi OS (64-bit recommended for Python 3.12 and Node 20). Check with `uname -m` (should report `aarch64` for 64-bit).
- Docker Engine (Docker CE). Install with the official convenience script or your package manager.
- Docker Compose plugin (recent Docker includes it). Confirm with `docker compose version`.
- Optional but recommended: `docker buildx` enabled (usually present by default). Confirm with `docker buildx version`.

Quick checklist (run on the Pi):
```bash
# Update OS
sudo apt update && sudo apt upgrade -y

# Install Docker (official convenience script)
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Enable/verify docker compose plugin
docker compose version

# Check architecture
uname -m
```

Environment and configuration
- Copy the example env and adapt for your LAN/production Pi.

```bash
cp .env.example .env.prod
# Edit `.env.prod` and set at minimum:
# POSTGRES_PASSWORD, SECRET_KEY, DOMAIN (or set DOMAIN to the Pi's local IP), CORS_ORIGINS
# Example: CORS_ORIGINS=http://192.168.1.42
# If you plan to access the site from other devices, set VITE_API_URL to http://<PI_IP>:80

# Use the Makefile helper to start production
make ENV=prod up
```

Notes about `.env.prod` values
- `POSTGRES_HOST` default in compose is `db` (internal Docker network). Keep that unless using an external DB.
- `CORS_ORIGINS` must include the frontend origin(s) (for Pi local network, that may be `http://<PI_IP>` or `http://<PI_HOSTNAME>:80`).

ARM image compatibility and `buildx`
- The backend `Dockerfile` references the `astral-sh/uv:latest` image via multi-stage copy. If that manifest does not publish an ARM variant, builds will fail on the Pi. Two options:
  1. Build multi-arch images on the Pi using `buildx` and `--platform linux/arm64` (or linux/arm/v7 for older Pi OS). This forces the build to target the Pi architecture.
  2. Build images on a cross-builder machine (your x86 laptop) using `docker buildx` with platforms including `linux/arm64`, then push to a registry and pull on the Pi.

Local single-device build (recommended for one-off Pi deployment):
```bash
# Create or switch to a builder that supports multi-platform builds
docker buildx create --use --name pantrypilot-builder || true

# Build images for local architecture only (faster)
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache

# Then start services
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d
```

If you need to explicitly target `linux/arm64` for buildx (e.g., running build on x86 machine):
```bash
docker buildx build --platform linux/arm64 -f ./apps/backend/Dockerfile -t pantrypilot_backend:prod ./apps/backend --load
docker buildx build --platform linux/arm64 -f ./apps/frontend/Dockerfile -t pantrypilot_frontend:prod ./apps/frontend --load
```

Networking and allowing phone access
- `docker-compose.prod.yml` maps port `80` on the host to Nginx. On the Pi this exposes the webapp on all interfaces by default. Verify `docker compose ps` to see port mappings.
- Find your Pi's IP on the LAN: `hostname -I` or `ip addr show`.
- From your phone, open `http://<PI_IP>/` in the browser. If you used the default `.env.prod`, `DOMAIN=localhost` might be set; you can update it to the Pi IP or a local hostname.

Nginx configuration notes
- The repository's `nginx/nginx.conf` and `nginx/conf.d/default.conf` bind to port 80 and proxy `/api/` to service `backend:8000` (internal Docker network). No changes required for LAN access.
- If you want to restrict Nginx to a single interface, edit the `listen` directive in `nginx/conf.d/default.conf` (e.g., `listen 192.168.1.42:80;`). By default `listen 80;` binds all interfaces.

Enabling HTTPS (optional)
- For local LAN test, HTTPS is optional. If you want HTTPS:
  - Use `scripts/https-setup.sh` (see README) to enable/disable. That script expects certs in `./ssl/certs` and `./ssl/private`.
  - For real domain + public exposure, use Let's Encrypt (Certbot) and open port 443 on your router.

Troubleshooting tips
- Container build fails due to missing arm manifest for a base image: either run buildx with `--platform` or replace the base image with an ARM-compatible one.
- Low memory / OOM: reduce backend worker count (set `WORKERS=1` in `.env.prod` or override in compose) and ensure swap is available.
- Service health checks fail: check logs `docker compose logs -f backend` and `docker compose logs -f nginx`.
- To run a shell in a container for debugging: `docker compose exec backend sh` or `docker compose exec frontend sh`.

Validation (smoke tests)
- From the Pi itself or another machine on your LAN:
```bash
# Health endpoints
curl http://<PI_IP>/health
curl http://<PI_IP>/api/v1/health

# Confirm frontend served
curl -I http://<PI_IP>/
```

Next steps and hardening
- Set up a small firewall on the Pi (ufw) to allow only ports 22 (SSH) and 80/443.
- Automate backups of the Postgres volume (`docker run --rm -v pantrypilot_postgres_data:/data -v $(pwd):/backup alpine sh -c "cd /data && tar czf /backup/db_backup.tgz ."`).
- Consider using a managed Postgres or a separate machine for DB if your Pi is resource constrained.

Appendix: Useful commands summary
```bash
# Build & start (production)
make ENV=prod up

# Or explicit compose commands (uses .env.prod)
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod build --no-cache
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod up -d

# View logs
docker compose --env-file .env.prod logs -f nginx backend frontend db

# Stop
docker compose --env-file .env.prod down

# List containers and ports
docker compose --env-file .env.prod ps

# Health checks
curl http://<PI_IP>/health
curl http://<PI_IP>/api/v1/health
```

---
Be cautious with production secrets and consider using a vault or environment injection when exposing the Pi to public networks. For local LAN usage the steps above should get you a working production-like deployment reachable from your phone.
```
