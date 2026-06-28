# Deploy on EC2 (single instance)

Runs the Python backend + the built 3D frontend on one Ubuntu EC2 box.
nginx serves the UI on port 80 and proxies `/api/v1/*` to the backend on 8080.
No Lambda, no API Gateway, no DynamoDB needed.

---

## 1. Launch an EC2 instance

- Region: **ap-south-1** (same as your Bedrock model)
- AMI: **Ubuntu Server 22.04 LTS**
- Type: **t3.small** (2 GB RAM)
- Key pair: create/select one (for SSH)
- **Security group inbound rules:**
  - SSH (22) from *My IP*
  - HTTP (80) from *Anywhere (0.0.0.0/0)*

### Give the instance Bedrock access (recommended: IAM role)

Best practice — no keys on disk:

1. IAM → Roles → Create role → Trusted entity: **AWS service → EC2**
2. Attach policy **AmazonBedrockFullAccess**
3. Name it e.g. `alexa-ec2-bedrock-role`
4. EC2 → your instance → Actions → Security → **Modify IAM role** → attach it

boto3 on the instance will use the role automatically. If you prefer keys
instead, skip the role and put them in `alexa-thinks-ahead/.env` (see step 3).

---

## 2. SSH in and clone

```bash
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
git clone <your-repo-url> ~/hackon_project
cd ~/hackon_project
```

---

## 3. Set the Bedrock config

Edit `alexa-thinks-ahead/.env` and make sure these are set:

```env
AWS_DEFAULT_REGION=ap-south-1
BEDROCK_REGION=ap-south-1
BEDROCK_MODEL_ID=mistral.mistral-large-2402-v1:0
```

- If you used an **IAM role** (step 1): leave `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` blank.
- If you're using **keys**: fill them in here. (`.env` is auto-loaded by the backend.)

> Never commit real keys. Confirm `.env` is in `.gitignore`.

---

## 4. Run the deploy script

```bash
bash deploy/ec2-setup.sh
```

It installs everything, builds the frontend, starts the backend as a service,
and configures nginx. When it finishes it prints your public URL.

---

## 5. Open the link

```
http://<EC2-PUBLIC-IP>
```

Share this with the judges. The 3D demo, CSV prediction (Bedrock), and
power-cut scenario all work.

---

## Operations

```bash
# Backend status / logs
sudo systemctl status alexa-backend
sudo journalctl -u alexa-backend -f

# After changing backend code
git pull && sudo systemctl restart alexa-backend

# After changing frontend code
git pull && cd demo && npm run build   # nginx serves the new dist immediately
```

The backend auto-restarts on crash and on reboot (systemd `Restart=always`).
On startup it pre-warms the Bedrock cache from `sample_activity_log.csv`, so the
first prediction in the demo is instant (watch the logs for the ✅ warm line).

---

## Cost & teardown

- t3.small ≈ $0.02/hr; Bedrock calls ≈ a few cents total.
- **Terminate the instance** when the hackathon is over to stop charges.

## Optional: HTTPS

If you need `https://` (some browsers restrict features on http), point a domain
at the instance and run:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```
