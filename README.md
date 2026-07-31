# Infrastructure Monitoring & Auto-Topology (MVP)

A centralized infrastructure monitoring and auto-topology application for physical servers, Hyper-V hosts/VMs, and Docker hosts/containers.

---

## Documentation Links
- 📘 [Deployment & Operations Guide](docs/Deployment_and_Operations_Guide.md)
- 📊 [Requirement Traceability Matrix (RTM)](docs/requirement_traceability_matrix.md)
- 🛡️ [Security, Backup & Operations Guide](docs/Operations_Backup_Monitoring.md)
- 📋 [Task Checklist & Progress Artifact](docs/task_checklist.md)

---

## Prerequisites
- **Docker Engine** v24+ & **Docker Compose** v2.20+
- **Python** 3.12+ (for local backend development)
- **Node.js** v20+ (for local frontend development)

---

## Quick Start (Docker Compose)

1. **Copy environment configuration**:
   ```bash
   cp .env.example .env
   ```

2. **Validate Compose configuration**:
   ```bash
   docker compose config
   ```

3. **Build and start the stack**:
   ```bash
   docker compose up -d --build
   ```

4. **Check service status and health**:
   ```bash
   docker compose ps
   ```

5. **Access Application**:
   - Web Dashboard & API Entrypoint: `http://localhost`
   - Backend Liveness Probe: `http://localhost/api/v1/health/live`
   - Backend Readiness Probe: `http://localhost/api/v1/health/ready`

---

## Test Suites Verification

### Backend Pytest Suite
```bash
cd backend
python -m pytest
```
> **Result**: 50 passed (100% PASSING)

### Frontend Vitest Suite & Production Build
```bash
cd frontend
npm test
npm run build
```
> **Result**: 4 component tests passed, 0 build errors.
