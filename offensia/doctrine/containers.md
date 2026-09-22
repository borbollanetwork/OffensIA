# OffensIA Doctrine — Containers & Kubernetes

Applies to container images, runtimes, and Kubernetes clusters. Activated
automatically when Kubernetes is discovered. The recurring theme is boundary
crossing: image → container → node → cluster → cloud.

## What to look for
- **Images**: embedded secrets, vulnerable/EOL base layers, build-time credentials
  in history, running as root, unnecessary tooling.
- **Runtime**: privileged containers, host mounts (docker.sock, hostPath),
  dangerous capabilities (CAP_SYS_ADMIN), host PID/net/IPC namespaces, writable
  host paths — all container-escape primitives.
- **Kubernetes RBAC**: over-broad roles/clusterroles, wildcard verbs/resources,
  ability to create pods / exec / read secrets / impersonate, escalate via
  workload identity.
- **Service accounts & workload identity**: default SA token mounted, SA bound to
  cloud roles (bridge into `cloud.md`).
- **Cluster surface**: exposed kubelet/API server, etcd exposure, admission gaps,
  network policy absence (flat cluster networking).
- **Supply chain**: unsigned images, mutable tags, registry exposure.

## When it applies / preconditions
- Cluster enumeration requires authorized access (kubeconfig/SA token) and the
  cluster in scope. An escape or RBAC-escalation claim requires demonstrating the
  crossing with a concrete artifact, not a manifest reading alone.

## Evidence required
- Container escape: the exploited primitive (mount/capability) plus proof of host
  reach (e.g. reading a host-only resource), with a negative control from a
  non-privileged pod.
- RBAC esc: the permission plus the performed/validated action and a negative
  control.

## Refuting false positives
`privileged: true` is OBSERVATION until an escape or host reach is demonstrated. A
broad ClusterRole is HYPOTHESIS until the escalation is shown. Network policy
absence is HARDENING unless lateral reach is demonstrated.

## Chaining
Pod with mounted SA token → RBAC read secrets → cloud role via workload identity →
`cloud.md`. Record each hop as an attack-graph edge with evidence.
