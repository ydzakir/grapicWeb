# Infrastructure Monitoring & Auto-Topology (MVP)

A centralized infrastructure monitoring and auto-topology application for physical servers, Hyper-V hosts/VMs, and Docker hosts/containers.

## Prerequisites
- Docker Engine v24+ & Docker Compose v2+
- Python 3.12+ (for local backend development)
- Node.js v20+ (for local frontend development)

## Quick Start (Docker Compose)

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Validate Compose configuration:
   ```bash
   docker compose config
   ```

3. Build and start the stack:
   ```bash
   docker compose up -d --build
   ```

4. Check service status and health:
   ```bash
   docker compose ps
   ```

5. Access Application:
   - Web Dashboard & API Entrypoint: `http://localhost`
   - Backend Liveness: `http://localhost/api/v1/health/live`
   - Backend Readiness: `http://localhost/api/v1/health/ready`

## Development Commands

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .[dev]

# Run tests
pytest

# Code checks
ruff check src tests
mypy src
```

### Frontend
```bash
cd frontend
npm install

# Run dev server
npm run dev

# Run tests & lint
npm run test
npm run lint
```
