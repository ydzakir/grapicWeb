# Task Checklist — Version 1.2 (Advanced Topology Views, Network Discovery, & Edge Provenance)

Dokumen pelacakan tugas untuk pengembangan fitur **Versi 1.2** aplikasi *Infrastructure Monitoring & Auto-Topology*.

---

## Stage Gates V1.2

### [x] V1.2 - Stage 1: Network Discovery Adapter & Database Provenance
- [x] Implement Network Discovery Schema (`subnets`, `network_edges`, `edge_provenance`, `confidence_score`)
- [x] Implement Network Discovery Capability Adapters (SNMP, ARP table parser, Traceroute/ICMP)
- [x] Implement Manual Mapping Fallback API with Audit Log tracking (`POST /api/v1/topology/edges/manual`)
- [x] Implement Edge Deduplication, Confidence Scoring (`high`, `medium`, `manual`), and Stale-Data Cleanup
- [x] Write unit & integration tests in `backend/tests/test_network_discovery.py`

### [x] V1.2 - Stage 2: Dual Topology Modes (Hierarchy View vs. Network View)
- [x] Implement REST API support for Hierarchy View vs Network Subnet/VLAN View (`GET /api/v1/topology?mode=hierarchy|network`)
- [x] Implement Subnet & VLAN grouping schema and Provenance metadata
- [x] Write topology query tests in `backend/tests/test_topology_modes.py`

### [x] V1.2 - Stage 3: Frontend Visual Animations & Motion Controls
- [x] Implement Status Pulse animation on node status change
- [x] Implement Animated Traffic Edges for links with verified telemetry traffic
- [x] Implement Animation Toggle switch & `prefers-reduced-motion` CSS media query support
- [x] Implement Mode Switcher (Hierarchy View vs Network View) on Topology Canvas

### [x] V1.2 - Stage 4: Manual Mapping Fallback UI & Provenance Inspector
- [x] Implement Manual Edge Creation Modal for Admin/Operator with Audit trail
- [x] Implement Edge Provenance & Confidence Indicator in React Flow Edge Tooltips
- [x] Write frontend component tests for Topology View Switcher & Animation Controls

### [x] V1.2 - Stage 5: Security, Performance Benchmark, & E2E Validation
- [x] Validate 250+ node network topology canvas rendering performance (FPS & response time)
- [x] Add E2E tests for View Mode switcher, Animation Toggle, and Manual Edge creation
- [x] Update Requirement Traceability Matrix (`docs/requirement_traceability_matrix.md`) with V1.2 features
