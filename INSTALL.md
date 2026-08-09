# INSTALL.md — install evo-skillopt as standalone software

Choose the path that matches how you want to run it:

| Path                                       | Best for                                                | Section |
|--------------------------------------------|---------------------------------------------------------|---------|
| **A. `pipx`** (recommended for laptops)    | Personal use, keeping deps isolated                      | [§ A](#a-pipx-recommended-for-laptops) |
| **B. `pip install -e .`**                  | Contributors and developers                              | [§ B](#b-editable-install-for-contributors) |
| **C. Docker (single container)**           | Quick self-host on a laptop or VPS                       | [§ C](#c-docker-single-container) |
| **D. Docker Compose**                      | Server self-host with restart-on-boot                    | [§ D](#d-docker-compose-server-self-host) |
| **E. Fly.io**                              | Global edge deploy in one command                        | [§ E](#e-flyio-cloud-deploy) |
| **F. Systemd service**                     | Long-running Linux server without containers             | [§ F](#f-systemd-linux-service) |
| **G. Kubernetes (Helm)**                   | Multi-tenant or enterprise                               | [§ G](#g-kubernetes-helm) |
| **H. Homebrew (macOS/Linux)**              | One-liner `brew install evo-skillopt` (tap-based)        | [§ H](#h-homebrew-macos--linux) |
| **I. Windows (WSL2 or native)**            | Windows 10/11 desktops                                   | [§ I](#i-windows-wsl2-or-native) |
| **J. Raspberry Pi / edge**                 | Low-power always-on box                                  | [§ J](#j-raspberry-pi--edge) |

Every path lands on the same `POST /train` HTTP contract described in
[`worker/README.md`](./worker/README.md).

---

## Prerequisites (common to every path)

- Python **3.10+** (3.12 recommended)
- `git`
- One or more LLM provider credentials (any of: OpenAI, Anthropic,
  Google, Azure OpenAI, local Ollama/vLLM). See [`.env.example`](./.env.example).
- A place to store data: at least a few GB of writable disk for
  training outputs.

Clone once:

```bash
git clone https://github.com/dnzengou/evo-skillopt.git
cd evo-skillopt
```

---

## A. `pipx` (recommended for laptops)

`pipx` installs the CLI into its own isolated venv and puts the console
script on your PATH — no environment pollution.

```bash
# Install pipx
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install evo-skillopt from source
pipx install .

# Or with worker extras
pipx install '.[worker]'

# Run
export WORKER_TOKEN="$(openssl rand -hex 32)"
python3 -m skillopt_worker &   # if you install worker extras, else:
python3 worker/skillopt_worker.py &

curl http://localhost:9000/health
```

Upgrade:

```bash
pipx reinstall evo-skillopt
```

---

## B. Editable install (for contributors)

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -e ".[dev,worker]"

# Sanity check
python -m py_compile worker/skillopt_worker.py
ruff check .
pytest -q                       # once tests are added
```

---

## C. Docker (single container)

```bash
# Build
docker build -f worker/Dockerfile -t evo-skillopt-worker:local .

# Run — mount ./data for persistent outputs
docker run --rm -d \
  --name evo-skillopt \
  -p 9000:9000 \
  -e WORKER_TOKEN="$(openssl rand -hex 32)" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v "$(pwd)/data:/data" \
  evo-skillopt-worker:local

curl http://localhost:9000/health
```

---

## D. Docker Compose (server self-host)

```bash
cp .env.example .env
$EDITOR .env                     # fill in WORKER_TOKEN + provider keys

docker compose -f worker/docker-compose.yml --env-file .env up --build -d
docker compose -f worker/docker-compose.yml logs -f worker
```

Compose declares a named volume (`evo-data`), restart-on-boot policy,
and a healthcheck. To stop:

```bash
docker compose -f worker/docker-compose.yml down
```

---

## E. Fly.io (cloud deploy)

Global, region-pinned, TLS-terminated. Free tier is enough to try it out.

```bash
# One-time
curl -L https://fly.io/install.sh | sh
fly auth login

cd worker

# Create the app (choose a unique name — Fly names are global)
fly apps create your-evo-skillopt-worker

# Storage for skill history / training outputs
fly volumes create evo_data --region ord --size 1

# Secrets
fly secrets set WORKER_TOKEN="$(openssl rand -hex 32)"
fly secrets set OPENAI_API_KEY="sk-..."
# fly secrets set ANTHROPIC_API_KEY="sk-ant-..."

# Deploy
fly deploy

# Verify
curl https://your-evo-skillopt-worker.fly.dev/health
# → {"service":"skillopt-worker","status":"ok"}
```

---

## F. Systemd (Linux service)

For teams that prefer bare-metal over containers.

```bash
# 1. Install as a system user
sudo useradd --system --home /opt/evo-skillopt --shell /usr/sbin/nologin evo
sudo git clone https://github.com/dnzengou/evo-skillopt.git /opt/evo-skillopt
sudo chown -R evo:evo /opt/evo-skillopt

# 2. Set up a venv
sudo -u evo python3 -m venv /opt/evo-skillopt/.venv
sudo -u evo /opt/evo-skillopt/.venv/bin/pip install --upgrade pip
sudo -u evo /opt/evo-skillopt/.venv/bin/pip install -e '/opt/evo-skillopt[worker]'

# 3. Environment file
sudo tee /etc/evo-skillopt.env >/dev/null <<'EOF'
WORKER_TOKEN=<random>
OPENAI_API_KEY=sk-...
OUTPUT_ROOT=/var/lib/evo-skillopt/outputs
EOF
sudo chmod 600 /etc/evo-skillopt.env
sudo chown evo:evo /etc/evo-skillopt.env
sudo mkdir -p /var/lib/evo-skillopt/outputs
sudo chown -R evo:evo /var/lib/evo-skillopt

# 4. Service unit
sudo tee /etc/systemd/system/evo-skillopt.service >/dev/null <<'EOF'
[Unit]
Description=evo-skillopt worker
After=network.target

[Service]
Type=simple
User=evo
Group=evo
WorkingDirectory=/opt/evo-skillopt
EnvironmentFile=/etc/evo-skillopt.env
ExecStart=/opt/evo-skillopt/.venv/bin/python /opt/evo-skillopt/worker/skillopt_worker.py
Restart=on-failure
RestartSec=5s
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/var/lib/evo-skillopt

[Install]
WantedBy=multi-user.target
EOF

# 5. Enable + start
sudo systemctl daemon-reload
sudo systemctl enable --now evo-skillopt.service
sudo systemctl status evo-skillopt.service
```

Front with nginx / Caddy for TLS if exposing publicly.

---

## G. Kubernetes (Helm)

A minimal deployment manifest — full Helm chart shipping in v0.4 (see
[`EvoSkillOpt_Blueprint.md § 5`](./EvoSkillOpt_Blueprint.md#5-capabilities)).

```yaml
# evo-skillopt-worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: evo-skillopt-worker }
spec:
  replicas: 1
  selector: { matchLabels: { app: evo-skillopt-worker } }
  template:
    metadata: { labels: { app: evo-skillopt-worker } }
    spec:
      containers:
        - name: worker
          image: ghcr.io/dnzengou/evo-skillopt-worker:latest
          ports: [{ containerPort: 9000 }]
          env:
            - { name: WORKER_TOKEN, valueFrom: { secretKeyRef: { name: evo-secrets, key: worker-token } } }
            - { name: OPENAI_API_KEY, valueFrom: { secretKeyRef: { name: evo-secrets, key: openai } } }
          volumeMounts:
            - { name: data, mountPath: /data }
          livenessProbe:
            httpGet: { path: /health, port: 9000 }
            initialDelaySeconds: 10
            periodSeconds: 30
      volumes:
        - name: data
          persistentVolumeClaim: { claimName: evo-skillopt-data }
---
apiVersion: v1
kind: Service
metadata: { name: evo-skillopt-worker }
spec:
  selector: { app: evo-skillopt-worker }
  ports:
    - port: 80
      targetPort: 9000
```

```bash
kubectl create secret generic evo-secrets \
  --from-literal=worker-token="$(openssl rand -hex 32)" \
  --from-literal=openai="$OPENAI_API_KEY"

kubectl apply -f evo-skillopt-worker.yaml
```

---

## H. Homebrew (macOS & Linux)

A tap-based install is planned for v0.2. Until then, use pipx (§ A).

```bash
# Planned:
brew tap dnzengou/evo-skillopt
brew install evo-skillopt

# Meanwhile (works today):
brew install pipx
pipx install git+https://github.com/dnzengou/evo-skillopt.git
```

---

## I. Windows (WSL2 or native)

**Recommended: WSL2** — Docker Desktop + WSL2 gives you the Linux
paths above with zero friction:

```powershell
wsl --install -d Ubuntu
# Reboot, then in the Ubuntu shell:
sudo apt update && sudo apt install -y python3-venv python3-pip git
git clone https://github.com/dnzengou/evo-skillopt.git
cd evo-skillopt
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[worker]'
python worker/skillopt_worker.py
```

**Native Windows** works too — install Python 3.12 from python.org,
then:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e '.[worker]'
$env:WORKER_TOKEN = "dev-token"
python worker\skillopt_worker.py
```

The worker itself is stdlib-only Python, so there are no
Windows-specific gotchas beyond path separators.

---

## J. Raspberry Pi / edge

Runs on a Pi 4 (4 GB RAM) or better. Provider API calls are the heavy
lifting — the worker itself is tiny.

```bash
# Pi OS 64-bit
sudo apt update && sudo apt install -y python3-venv python3-pip git docker.io
sudo usermod -aG docker "$USER"      # log out/in

git clone https://github.com/dnzengou/evo-skillopt.git
cd evo-skillopt

cp .env.example .env && $EDITOR .env
docker compose -f worker/docker-compose.yml --env-file .env up --build -d
```

For truly small boards, self-host with a local LLM (Ollama) on a
laptop and point the Pi worker at it via `OPENAI_API_BASE`.

---

## Verifying the install

Regardless of path:

```bash
# 1. Liveness
curl http://localhost:9000/health
# → {"service":"skillopt-worker","status":"ok"}

# 2. Auth
curl -X POST http://localhost:9000/train \
  -H "Authorization: Bearer $WORKER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bot_id":"probe/x"}'
# → 500 with "training-failed" body but confirms the auth + routing path.

# 3. Full smoke (multiple endpoints)
bash scripts/smoke.sh
```

## Uninstall

- **pipx:** `pipx uninstall evo-skillopt`
- **pip / editable:** delete the venv
- **Docker:** `docker rm -f evo-skillopt` + `docker volume rm evo-data`
- **Compose:** `docker compose -f worker/docker-compose.yml down -v`
- **Fly.io:** `fly apps destroy your-evo-skillopt-worker`
- **Systemd:** `sudo systemctl disable --now evo-skillopt` + remove
  `/opt/evo-skillopt`, `/etc/evo-skillopt.env`, `/var/lib/evo-skillopt`

---

## Next step

Once the worker is up, follow [`USE_CASES.md`](./USE_CASES.md) to pick
your first pattern and wire your signal source into `POST /train`.
