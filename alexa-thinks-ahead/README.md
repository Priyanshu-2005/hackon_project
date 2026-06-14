# Alexa Thinks Ahead

Proactive AI-Powered Smart Home System for HackOn with Amazon Season 6.0.

## Overview

Alexa Thinks Ahead is a proactive smart home system that leverages Amazon Bedrock Claude Sonnet as its reasoning engine to anticipate household needs, automate device orchestration across 10 connected devices, and deliver contextual intelligence through a 5-tier autonomy model.

Built around the Sharma family persona, the platform demonstrates how Alexa can evolve from reactive voice commands to genuinely anticipatory home management.

## Architecture

The system operates on a continuous four-stage cognitive pipeline:

- **SENSE** — Ingests data from 10 device sensors, environmental monitors, and historical patterns
- **THINK** — Amazon Bedrock Claude Sonnet processes fused context to identify patterns and predict needs
- **ACT** — Based on autonomy tier, executes actions or delivers recommendations
- **EXPLAIN** — Every action is accompanied by a natural language explanation

## Tech Stack

- **AI/ML**: Amazon Bedrock Claude Sonnet
- **Compute**: AWS Lambda (Python 3.10)
- **Storage**: DynamoDB (on-demand)
- **Events**: Amazon EventBridge
- **API**: API Gateway (REST, JWT auth)
- **Voice**: Alexa Smart Home Skill API
- **IaC**: AWS SAM
- **Region**: ap-south-1 (Mumbai)

## Project Structure

```
alexa-thinks-ahead/
├── src/
│   ├── devices/          # Device adapters for all 10 devices
│   ├── context/          # Context engine, sensor fusion, patterns
│   ├── intelligence/     # Proactive engine, predictions
│   ├── autonomy/         # Trust scoring, tier management
│   ├── learning/         # Continuous learning, feedback
│   ├── reasoning/        # Bedrock Claude Sonnet integration
│   ├── handlers/         # Lambda handlers (skill, API, events)
│   ├── models/           # Data models (dataclasses)
│   └── utils/            # Configuration, logging, helpers
├── tests/
│   ├── unit/
│   └── integration/
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Testing

```bash
pytest
```

## Devices Supported

| Device | Category | Brand |
|--------|----------|-------|
| Living Room AC | Climate | Daikin |
| Smart Lights | Lighting | Philips Hue |
| Security Camera | Security | Ring |
| Smart Lock | Security | Yale |
| Kitchen Appliance Hub | Kitchen | Samsung |
| Water Purifier | Utility | Kent |
| Smart Geyser | Utility | Havells |
| Inverter/UPS | Power | Luminous |
| Smart TV | Entertainment | Fire TV |
| Echo Devices | Assistant | Amazon |

## Autonomy Tiers

| Level | Name | Description |
|-------|------|-------------|
| 1 | Inform | Notify user of observations |
| 2 | Suggest | Recommend actions with rationale |
| 3 | Auto-Act (Reversible) | Execute reversible actions automatically |
| 4 | Auto-Act (Irreversible) | Execute with confirmation for high-impact |
| 5 | Full Autonomy | Learned preferences, no confirmation needed |
