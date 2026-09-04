# ADR-001: Native integration migration

## Decision

Load Analyser will be a Home Assistant custom integration distributed through
HACS. The former App remains a read-only behavioural reference during migration.
No migration code may call, restart, reconfigure, or write to the running App.

Each appliance is represented by one config entry and one device. Calculation
logic remains independent from Home Assistant-facing entity code.

## State contract

- Home Assistant `Store` owns persistence.
- Raw cycle traces and learned aggregate models are distinct records.
- Stored data has an explicit schema version and migration path.
- Cycle finalisation must be idempotent.
- Unknown, unavailable, malformed and stale source data are explicit states.
- Diagnostics expose categories and counts, not entity IDs, credentials or
  device/account identifiers.

## Safety boundary

The first native releases are advisory. Direct appliance execution will only be
enabled after the old package's request, revalidation, start, confirmation,
cancellation, failure and restart behaviours have regression coverage in the
new repository.

## Compatibility

Legacy YAML and dashboard files are kept as examples for entity-contract mapping.
The integration will not overwrite user-owned YAML or dashboards.
