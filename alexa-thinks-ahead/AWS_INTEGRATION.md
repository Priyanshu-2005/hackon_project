# AWS Integration Guide

This guide takes the **local, fully-working demo** and connects it to real AWS
services (Bedrock, DynamoDB, Lambda, API Gateway, EventBridge). The local demo
keeps working the whole time — AWS is opt-in via environment variables, so you
can flip between "local mock" and "live AWS" without code changes.

> **Audience:** someone who already ran the local demo (`python3 demo.py --api`
> + `npm run dev`) and now wants it on AWS.

---

## 0. What is already done vs. what you do here

| Area | Status | Where |
|------|--------|-------|
| SAM template (5 Lambdas, 4 DynamoDB tables, API Gateway, EventBridge) | ✅ Done | `template.yaml` |
| Bedrock reasoning client (boto3, retries, timeout) | ✅ Done | `src/reasoning/client.py` |
| Reasoning proxy Lambda entry point | ✅ Done (added) | `src/reasoning/client.py:lambda_handler` |
| Env-aware config (tables, model id, region from env vars) | ✅ Done (added) | `src/utils/config.py` |
| REST API handlers (devices, context, patterns, tiers, scenario) | ✅ Done | `src/handlers/api_handler.py` |
| Frontend pointed at a configurable backend URL + auth | ✅ Done (added) | `demo/src/data/ApiProvider.js`, `demo/.env.example` |
| **AWS account + credentials** | ⬜ You do | Step 1 |
| **Bedrock model access (Claude)** | ⬜ You do | Step 2 |
| **`sam build && sam deploy`** | ⬜ You do | Step 4 |
| **Point the frontend at API Gateway** | ⬜ You do | Step 6 |
| **(Optional) Live DynamoDB-backed data** | ⬜ Optional | Step 8 |
| **(Optional) Alexa skill + API auth** | ⬜ Optional | Step 9 |

The API handler currently serves **deterministic simulated device state**
(`src/devices/demo_states.py`) — which is ideal for a reliable live demo. Step 8
shows how to switch specific endpoints to real DynamoDB reads if you want.

---

## 1. Prerequisites

Install and verify these once:

```bash
# AWS CLI v2
aws --version

# AWS SAM CLI
sam --version

# Python 3.10 (matches the Lambda runtime in template.yaml)
python3 --version
```

Configure credentials for an IAM user/role that can create the stack
(Lambda, DynamoDB, API Gateway, EventBridge, IAM, CloudFormation, S3) and call
Bedrock:

```bash
aws configure
# AWS Access Key ID:     <your key>
# AWS Secret Access Key: <your secret>
# Default region name:   ap-south-1
# Default output format:  json

# Sanity check
aws sts get-caller-identity
```

---

## 2. Enable Bedrock model access

Bedrock requires you to **request access** to a model before you can invoke it.

1. Open the Bedrock console in **ap-south-1** (Mumbai).
2. Go to **Model access** → **Manage model access**.
3. Enable **Anthropic Claude 3 Sonnet** and submit. Access is usually granted in
   a few minutes.
4. Confirm the exact model id (the template + config default to
   `anthropic.claude-3-sonnet-20240229-v1:0`):

```bash
aws bedrock list-foundation-models --region ap-south-1 \
  --query "modelSummaries[?contains(modelId,'claude-3-sonnet')].modelId" --output table
```

> If Claude 3 Sonnet is not offered in `ap-south-1`, pick a region/model that is,
> then update `BEDROCK_REGION` + `BEDROCK_MODEL_ID` (see Step 3) and the model
> ARN/region in `template.yaml`.

---

## 3. Configure environment variables

The backend reads configuration from environment variables and falls back to
local defaults when they are unset (see `src/utils/config.py`). Copy the example
and fill it in:

```bash
cd alexa-thinks-ahead
cp .env.example .env
```

Key variables (most have working defaults):

| Variable | Purpose | Default |
|----------|---------|---------|
| `AWS_DEFAULT_REGION` | Region for all AWS calls | `ap-south-1` |
| `BEDROCK_MODEL_ID` | Claude model id | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `BEDROCK_REGION` | Region for Bedrock | falls back to `AWS_DEFAULT_REGION` |
| `STAGE` | Deployment stage (`dev`/`staging`/`prod`) | `dev` |
| `DEVICE_STATE_TABLE` etc. | DynamoDB table names | stage-suffixed names |
| `SAM_S3_BUCKET` | Artifact bucket (optional; `--guided` creates one) | empty |

> **You do not have to hand-set the table-name vars for deployment** — the SAM
> template injects the correct stage-suffixed names into each Lambda
> automatically (see `Globals.Function.Environment` in `template.yaml`). The
> `.env` values are for **local** runs that talk to AWS.

---

## 4. Build and deploy the stack

From the `alexa-thinks-ahead/` directory:

```bash
sam build

# First deploy: interactive, saves answers to samconfig.toml
sam deploy --guided
#   Stack Name:                  alexa-thinks-ahead
#   AWS Region:                  ap-south-1
#   Parameter Stage:             dev
#   Confirm changes before deploy: Y
#   Allow SAM CLI IAM role creation: Y
#   Disable rollback:            N
#   Save arguments to configuration file: Y
```

Subsequent deploys are just:

```bash
sam build && sam deploy
```

When it finishes, copy the **stack outputs** — especially `ApiUrl`:

```bash
aws cloudformation describe-stacks --stack-name alexa-thinks-ahead \
  --query "Stacks[0].Outputs" --output table
```

You'll see `ApiUrl`, the four table names, the event bus name, and each Lambda
ARN.

---

## 5. Smoke-test the deployed backend

### 5a. Bedrock connectivity (Reasoning Proxy Lambda)

```bash
aws lambda invoke --function-name alexa-thinks-ahead-reasoning-dev \
  --payload '{"prompt":"Reply with the single word: ready"}' \
  --cli-binary-format raw-in-base64-out /dev/stdout
```

A `200` with model text confirms IAM + Bedrock model access are correct. A `502`
means Bedrock is reachable but the invocation failed (usually model access not
yet granted — re-check Step 2).

### 5b. REST API

> The API Gateway has a **JWT authorizer enabled by default** in `template.yaml`.
> For an unauthenticated demo, see Step 7 to disable it, otherwise these calls
> return `401`.

```bash
API_URL=$(aws cloudformation describe-stacks --stack-name alexa-thinks-ahead \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)

curl "$API_URL/devices"
curl "$API_URL/context/snapshot"
```

> Note: deployed gateway routes live at the **stage root** (`$API_URL/devices`),
> **not** under `/api/v1`. The frontend handles this via `VITE_API_PREFIX`
> (Step 6).

---

## 6. Point the frontend at AWS

The frontend defaults to the local backend. Override it with Vite env vars
(see `demo/.env.example`):

```bash
cd demo
cp .env.example .env.local
```

Edit `.env.local`:

```bash
# Full API Gateway stage URL from the SAM `ApiUrl` output
VITE_API_BASE_URL=https://abc123.execute-api.ap-south-1.amazonaws.com/dev
# Gateway routes are at the stage root, so clear the local /api/v1 prefix
VITE_API_PREFIX=
# Only if the JWT authorizer is enabled (Step 7)
VITE_API_AUTH_TOKEN=
```

Restart the dev server and toggle the UI to **real** mode:

```bash
npm run dev
```

> **Local demo unchanged:** with no `.env.local`, the frontend still uses
> `http://localhost:8080` + `/api/v1`, so your offline demo keeps working.

---

## 7. CORS and API authentication

**CORS** is already configured on the API Gateway (`Cors` block in
`template.yaml`, `AllowOrigin: '*'`). For production, replace `'*'` with your
exact frontend origin.

**Auth:** the template ships with a Cognito JWT authorizer
(`SmartHomeApi.Auth.DefaultAuthorizer`). Two options:

- **Demo (no auth):** comment out the `Auth:` block under `SmartHomeApi` in
  `template.yaml`, then `sam build && sam deploy`. Leave `VITE_API_AUTH_TOKEN`
  empty.
- **With auth:** stand up a Cognito user pool, set the authorizer `issuer`/
  `audience` to match, obtain a token, and put it in `VITE_API_AUTH_TOKEN`.

> ⚠️ Disabling auth makes every endpoint public. Only do this for a short-lived
> demo, never for shared/public deployments.

---

## 8. (Optional) Serve live DynamoDB data instead of simulated state

The API handler returns deterministic data from `src/devices/demo_states.py`,
which is great for a predictable demo. To back specific endpoints with real
DynamoDB data:

1. Seed device state (the Context Engine Lambda also writes here on its 1-minute
   schedule, but you can seed manually):

   ```bash
   aws dynamodb put-item --table-name alexa-thinks-ahead-device-states-dev \
     --item '{"device_id":{"S":"living_room_ac"},"timestamp":{"S":"2024-06-13T17:40:00+00:00"},"status":{"S":"online"},"properties":{"M":{"temperature":{"N":"24"}}}}'
   ```

2. In `src/handlers/api_handler.py`, read from DynamoDB inside the relevant
   handler. The config singleton already exposes the correct (env-injected)
   table name:

   ```python
   import boto3
   from src.utils.config import get_config

   def _table():
       return boto3.resource("dynamodb").Table(get_config().device_state_table)

   # Example: query latest state for one device
   # _table().query(KeyConditionExpression=Key("device_id").eq(device_id), ...)
   ```

3. The API Handler Lambda already has `DynamoDBCrudPolicy` / `DynamoDBReadPolicy`
   for these tables in `template.yaml`, so no IAM change is needed.

> Keep the `demo_states` fallback so the demo still works if a table is empty.

---

## 9. (Optional) Alexa skill + EventBridge

- **Alexa skill:** create a Smart Home skill in the Alexa Developer Console, set
  its endpoint to the `SkillHandlerFunctionArn` output, and put the skill id in
  `ALEXA_SKILL_ID` in `.env`.
- **EventBridge:** the `EventProcessorFunction` is already subscribed to the
  `smart-home.device` source on the custom bus. Publish a test event:

  ```bash
  aws events put-events --entries '[{
    "Source":"smart-home.device",
    "DetailType":"power_cut",
    "Detail":"{\"grid_status\":\"offline\",\"battery_level\":80}",
    "EventBusName":"alexa-thinks-ahead-events-dev"
  }]'
  ```

  Then check the logs: `sam logs -n EventProcessorFunction --stack-name alexa-thinks-ahead --tail`.

---

## 10. Useful operations

```bash
# Tail logs for any function
sam logs -n APIHandlerFunction --stack-name alexa-thinks-ahead --tail

# Redeploy after code changes
sam build && sam deploy

# Tear everything down (deletes tables + data)
sam delete --stack-name alexa-thinks-ahead
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `AccessDeniedException` on Bedrock | Model access not granted | Step 2 |
| Reasoning Lambda returns `502` | Wrong model id / region | Match `BEDROCK_MODEL_ID` + `BEDROCK_REGION` to an enabled model |
| API calls return `401` | JWT authorizer enabled | Step 7 (disable for demo or pass a token) |
| Frontend hits `/api/v1/...` on gateway and 404s | Prefix mismatch | Set `VITE_API_PREFIX=` (empty) in `.env.local` |
| Lambda uses wrong table name | Stale config | Tables come from env vars now; redeploy so SAM re-injects them |
| `ResourceNotFoundException` on DynamoDB | Reading a table before seeding | Step 8, or keep the `demo_states` fallback |

---

## Summary of what changed to make this smooth

These edits were made so AWS integration needs **config, not code changes**:

1. **`src/utils/config.py`** — now reads table names, region, model id, stage,
   and log level from environment variables (with local defaults). Fixed the
   Bedrock model id default to the valid `...-20240229-v1:0` id.
2. **`src/reasoning/client.py`** — added the `lambda_handler` that
   `template.yaml`'s `ReasoningProxyFunction` references, so that function is
   deployable and invokable.
3. **`demo/src/data/ApiProvider.js`** — base URL, path prefix, and an optional
   Bearer token are now configurable via `VITE_*` env vars; defaults preserve
   the local demo exactly.
4. **`demo/.env.example`** — documents the frontend variables for pointing at
   API Gateway.
