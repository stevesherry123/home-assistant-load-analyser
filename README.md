# Home Assistant Load Analyser

Load Analyser is a native Home Assistant custom integration that learns appliance
power profiles and recommends economical times and programs to run flexible loads.

> **Development status:** migration from the Load Optimizer Home Assistant App is
> in progress. Do not replace a production installation until the published
> migration and parity checks are complete.

## Current capabilities

- UI configuration with Home Assistant entity selectors
- one independently reloadable config entry per appliance
- restart-safe cycle capture in Home Assistant storage
- raw cycle traces retained separately from aggregate program models
- profile-derived energy and optional meter-delta comparison
- learned runtime, energy, representative profile and confidence
- tariff parsing and profile-aware cost optimisation
- native sensors, device registration, diagnostics and maintenance buttons
- HACS-compatible repository layout

## Installation for development

1. Add this repository to HACS as a custom **Integration** repository.
2. Install **Load Analyser** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration**.
4. Select **Load Analyser** and choose the appliance source entities.

The integration is advisory during migration. Appliance execution remains
disabled until its safety workflow reaches tested parity with the existing App.

## Architecture

The native adapter is intentionally separate from the calculation engine:

```text
Home Assistant entities → coordinator → raw cycle store → learned models
                                                ↓
tariff entity → normaliser → profile costing → recommendation entities
```

Historical App packages and dashboard definitions are retained under `examples/`
for parity mapping; they are not installed or allowed to modify a running system.

## Development

Run the dependency-free engine tests with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

See `docs/adr-001-native-integration.md` for migration boundaries and safety rules.
