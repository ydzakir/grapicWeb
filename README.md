# Infrastructure Monitoring & Auto-Topology (Version 2.0 Enterprise Release)

A centralized, enterprise-grade infrastructure monitoring, auto-topology visualization, and governance system for physical servers, Hyper-V hosts/VMs, Docker containers, and Cloudflare edge services.

---

## 🌟 Version 2.0 Key Subprojects (100% Completed)

1. 🛡️ **Advanced User Management & Granular RBAC**: Role definitions (`ADMIN`, `OPERATOR`, `VIEWER`), action-level custom permissions, and node group scoping.
2. 🔑 **Enterprise SSO & LDAP / OpenID Connect (OIDC)**: Multi-driver authentication (Local, LDAP/Active Directory, Keycloak/Okta OIDC SSO) with auto-provisioning & group mapping.
3. 📄 **Historical PDF & Excel Reports**: Automated executive summary reports generation and download endpoints.
4. 📧 **Scheduled Automated Report Email Delivery**: Cron scheduler engine delivering HTML executive summary emails with PDF/Excel attachments.
5. ⏳ **Topology History & Time-Travel Viewer**: Versioned topology canvas snapshot diff viewer.
6. 🌐 **Cloudflare Edge Status Integration**: Cloudflare status API collector, DNS health check, and edge disruption alerts.
7. 🎫 **ITSM Ticketing Integration (Jira / ServiceNow)**: Automated incident ticket creation, status synchronization, and manual ticket drawer.
8. 🔐 **External Secrets Provider (HashiCorp Vault)**: Vault Transit & KV-v2 integration with key rotation and fallback provider.
9. ⚡ **Active-Active High Availability & Node Redundancy**: HA cluster heartbeat, leader election, and failover synchronization.
10. 📋 **Governance Workflow & Quarterly Audit Review**: Account snapshot audit campaigns, decision submission, reviewer escalation engine, and SHA-256 executive digital sign-off.

---

## 📘 Documentation Links
- 📖 [Master SESSION Audit Record](SESSION.md)
- 📋 [Task Checklist v2.0](docs/task_checklist_v2.0.md)
- 📘 [Deployment & Operations Guide](docs/Deployment_and_Operations_Guide.md)
- 📊 [Requirement Traceability Matrix (RTM)](docs/requirement_traceability_matrix.md)
- 🛡️ [Security, Backup & Operations Guide](docs/Operations_Backup_Monitoring.md)

---

## 🔐 Demo Credentials (Development Only — Change Before Production)

> ⚠️ **Security notice**: The credentials below are for **local development only**. Before any
> production deployment, replace `BOOTSTRAP_ADMIN_PASSWORD` and `SECRET_KEY` in your `.env`
> (see `.env.example`). The backend refuses to start in `ENVIRONMENT=production` with a
> placeholder secret. Demo accounts are created by the bootstrap/seed scripts only.

- **Local Admin Demo**: `admin@infra.com` / `AdminSecurePass123!`
- **LDAP Demo Account**: `ldapuser` / `LdapSecurePass123!`
- **Enterprise OIDC SSO**: Click *"Login with Enterprise OIDC / Single Sign-On"* on the login page.

---

## 🚀 Quick Start (Docker Compose)

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

## 🧪 Test Suites Verification

### Backend Pytest Suite (90/90 Passing)
```bash
cd backend
backend\.venv\Scripts\pytest.exe backend/tests
```
> **Result**: `90 passed` (100% PASSING, 0 failures)

### Frontend Vitest Suite & Production Build
```bash
cd frontend
npm test
npm run build
```
> **Result**: 4 component tests passed, 0 build errors.
