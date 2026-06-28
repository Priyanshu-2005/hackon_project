# #!/usr/bin/env bash
# # ============================================================
# # Alexa Thinks Ahead — one-shot EC2 deployment
# # ============================================================
# # Run this ONCE on a fresh Ubuntu 22.04 EC2 instance, from the
# # root of the cloned repository:
# #
# #   git clone <your-repo-url> ~/hackon_project
# #   cd ~/hackon_project
# #   bash deploy/ec2-setup.sh
# #
# # It installs dependencies, builds the frontend, configures nginx
# # (serves the UI on port 80 and proxies /api/v1 -> backend:8080),
# # and runs the Python backend as a systemd service that survives
# # reboots and SSH disconnects.
# #
# # AWS credentials for Bedrock: PREFERRED is an IAM instance role
# # (no keys on disk). Otherwise put them in alexa-thinks-ahead/.env
# # (the backend auto-loads that file).
# # ============================================================
# set -euo pipefail

# # --- Resolve paths ------------------------------------------------------------
# REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# BACKEND_DIR="$REPO_ROOT/alexa-thinks-ahead"
# FRONTEND_DIR="$REPO_ROOT/demo"
# RUN_USER="$(whoami)"

# echo "==> Repo root:   $REPO_ROOT"
# echo "==> Backend dir: $BACKEND_DIR"
# echo "==> Frontend dir:$FRONTEND_DIR"
# echo "==> Run user:    $RUN_USER"

# # --- 1. System packages -------------------------------------------------------
# echo "==> Installing system packages..."
# sudo apt-get update -y
# sudo apt-get install -y python3-pip python3-venv nginx curl git

# # Node 20 (Ubuntu's apt node is too old for Vite)
# if ! command -v node >/dev/null 2>&1 || [ "$(node -v | cut -dv -f2 | cut -d. -f1)" -lt 18 ]; then
#   echo "==> Installing Node.js 20..."
#   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
#   sudo apt-get install -y nodejs
# fi
# echo "    node $(node -v), npm $(npm -v)"

# # --- 2. Backend Python deps ---------------------------------------------------
# echo "==> Installing backend Python dependencies..."
# cd "$BACKEND_DIR"
# pip3 install --user -r requirements.txt

# # --- 3. Build the frontend (same-origin: nginx proxies /api/v1) ---------------
# echo "==> Building frontend..."
# cd "$FRONTEND_DIR"
# cat > .env.production <<'EOF'
# VITE_API_BASE_URL=
# VITE_API_PREFIX=/api/v1
# VITE_API_AUTH_TOKEN=
# EOF
# npm install
# npm run build
# echo "    Built -> $FRONTEND_DIR/dist"

# # --- 4. systemd service for the backend --------------------------------------
# echo "==> Installing systemd service (alexa-backend)..."
# sudo tee /etc/systemd/system/alexa-backend.service >/dev/null <<EOF
# [Unit]
# Description=Alexa Thinks Ahead API backend
# After=network.target

# [Service]
# Type=simple
# User=$RUN_USER
# WorkingDirectory=$BACKEND_DIR
# # PATH so the pip --user installed packages + python are found
# Environment=PATH=/usr/bin:/usr/local/bin:$HOME/.local/bin
# # AWS region/model also come from $BACKEND_DIR/.env (auto-loaded by demo.py)
# ExecStart=/usr/bin/python3 $BACKEND_DIR/demo.py --api
# Restart=always
# RestartSec=3

# [Install]
# WantedBy=multi-user.target
# EOF

# sudo systemctl daemon-reload
# sudo systemctl enable alexa-backend
# sudo systemctl restart alexa-backend

# # --- 5. nginx site ------------------------------------------------------------
# echo "==> Configuring nginx..."
# sudo tee /etc/nginx/sites-available/alexa >/dev/null <<EOF
# server {
#     listen 80 default_server;
#     server_name _;

#     root $FRONTEND_DIR/dist;
#     index index.html;

#     # Proxy API calls to the Python backend on port 8080
#     location /api/v1/ {
#         proxy_pass http://127.0.0.1:8080/api/v1/;
#         proxy_set_header Host \$host;
#         proxy_set_header X-Real-IP \$remote_addr;
#         proxy_read_timeout 120s;   # Bedrock calls can take ~30s
#     }

#     # SPA fallback
#     location / {
#         try_files \$uri \$uri/ /index.html;
#     }
# }
# EOF

# sudo ln -sf /etc/nginx/sites-available/alexa /etc/nginx/sites-enabled/alexa
# sudo rm -f /etc/nginx/sites-enabled/default
# sudo nginx -t
# sudo systemctl restart nginx

# # --- Done ---------------------------------------------------------------------
# PUBLIC_IP="$(curl -s --max-time 3 http://169.254.169.254/latest/meta-data/public-ipv4 || echo '<EC2-PUBLIC-IP>')"
# echo ""
# echo "============================================================"
# echo " ✅ Deploy complete."
# echo "    Open:  http://$PUBLIC_IP"
# echo ""
# echo " Backend:  sudo systemctl status alexa-backend"
# echo " Logs:     sudo journalctl -u alexa-backend -f"
# echo " Rebuild FE after code change:  cd $FRONTEND_DIR && npm run build"
# echo " Restart BE after code change:  sudo systemctl restart alexa-backend"
# echo "============================================================"
#!/usr/bin/env bash
# ============================================================
# Alexa Thinks Ahead — one-shot EC2 deployment
# ============================================================
# Run this ONCE on a fresh Ubuntu 22.04/24.04 EC2 instance,
# from the root of the cloned repository:
#
#   git clone <your-repo-url> ~/hackon_project
#   cd ~/hackon_project
#   bash deploy/ec2-setup.sh
#
# It installs dependencies, builds the frontend, configures nginx
# (serves the UI on port 80 and proxies /api/v1 -> backend:8080),
# and runs the Python backend as a systemd service that survives
# reboots and SSH disconnects.
#
# AWS credentials for Bedrock: PREFERRED is an IAM instance role
# (no keys on disk). Otherwise put them in alexa-thinks-ahead/.env
# (the backend auto-loads that file).
# ============================================================
set -euo pipefail

# --- Resolve paths ------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/alexa-thinks-ahead"
FRONTEND_DIR="$REPO_ROOT/demo"
VENV_DIR="$BACKEND_DIR/.venv"
RUN_USER="$(whoami)"

echo "==> Repo root:   $REPO_ROOT"
echo "==> Backend dir: $BACKEND_DIR"
echo "==> Frontend dir:$FRONTEND_DIR"
echo "==> Venv dir:    $VENV_DIR"
echo "==> Run user:    $RUN_USER"

# --- 1. System packages -------------------------------------------------------
echo "==> Installing system packages..."
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv python3-full nginx curl git

# Node 20 (Ubuntu's apt node is too old for Vite)
if ! command -v node >/dev/null 2>&1 || [ "$(node -v | cut -dv -f2 | cut -d. -f1)" -lt 18 ]; then
  echo "==> Installing Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
echo "    node $(node -v), npm $(npm -v)"

# --- 2. Backend Python deps (venv — works on Ubuntu 22.04 and 24.04) ----------
echo "==> Creating Python virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "==> Installing backend Python dependencies into venv..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

# --- 3. Build the frontend (same-origin: nginx proxies /api/v1) ---------------
echo "==> Building frontend..."
cd "$FRONTEND_DIR"
cat > .env.production <<'EOF'
VITE_API_BASE_URL=
VITE_API_PREFIX=/api/v1
VITE_API_AUTH_TOKEN=
EOF
npm install
npm run build
echo "    Built -> $FRONTEND_DIR/dist"

# --- 4. systemd service for the backend --------------------------------------
echo "==> Installing systemd service (alexa-backend)..."
sudo tee /etc/systemd/system/alexa-backend.service >/dev/null <<EOF
[Unit]
Description=Alexa Thinks Ahead API backend
After=network.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$BACKEND_DIR
# Use the venv's Python so all pip packages are available
ExecStart=$VENV_DIR/bin/python $BACKEND_DIR/demo.py --api
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable alexa-backend
sudo systemctl restart alexa-backend

# --- 5. nginx site ------------------------------------------------------------
echo "==> Configuring nginx..."
sudo tee /etc/nginx/sites-available/alexa >/dev/null <<EOF
server {
    listen 80 default_server;
    server_name _;

    root $FRONTEND_DIR/dist;
    index index.html;

    # Proxy API calls to the Python backend on port 8080
    location /api/v1/ {
        proxy_pass http://127.0.0.1:8080/api/v1/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 120s;   # Bedrock calls can take ~30s
    }

    # SPA fallback
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/alexa /etc/nginx/sites-enabled/alexa
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# --- Done ---------------------------------------------------------------------
PUBLIC_IP="$(curl -s --max-time 3 http://169.254.169.254/latest/meta-data/public-ipv4 || echo '<EC2-PUBLIC-IP>')"
echo ""
echo "============================================================"
echo " ✅ Deploy complete."
echo "    Open:  http://$PUBLIC_IP"
echo ""
echo " Backend:  sudo systemctl status alexa-backend"
echo " Logs:     sudo journalctl -u alexa-backend -f"
echo " Rebuild FE: cd $FRONTEND_DIR && npm run build"
echo " Restart BE: sudo systemctl restart alexa-backend"
echo " Venv pip:   $VENV_DIR/bin/pip install <package>"
echo "============================================================"