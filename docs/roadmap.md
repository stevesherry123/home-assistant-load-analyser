# Prototype roadmap

This repository is a native-integration migration prototype. Consult the
[parity matrix](parity-matrix.md), [architecture](architecture.md) and
[migration decision](adr-001-native-integration.md) before considering adoption.
A roadmap is not proof of parity or permission to replace a running installation.

## Priorities

- Design a deliberate, validated learning-state import with schema migration.
- Improve appliance/programme-policy editing without changing stable identities.
- Complete request, revalidation, start, confirmation, cancellation, failure and
  restart regression coverage before enabling appliance commands.
- Preserve recovery behaviour and explain actionable problems through HA Repairs.
- Provide optional native dashboard guidance without overwriting user-owned YAML.

Keep the calculation engine independent of HA/provider adapters. Preserve raw
cycle observations separately from aggregate models, and validate unknown,
missing and corrected inputs explicitly. Keep control advisory until the
required end-to-end safety and migration checks pass.

Historical detailed planning is maintained separately; public documentation
retains the prototype's current contract and limitations. This documentation
cleanup does not retire the project or establish equivalence with Load Optimizer.
