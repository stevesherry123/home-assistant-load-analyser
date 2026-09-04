# App-to-integration parity matrix

This matrix prevents copied reference files from being mistaken for native parity.

| Capability | Native status | Notes |
|---|---|---|
| Multi-appliance configuration | Implemented | One reloadable config entry per appliance |
| Cycle detection and sampling | Implemented | Persistent active capture |
| Raw cycle retention | Implemented | Separate from aggregates |
| Program learning | Implemented | Runtime, energy, profile, confidence |
| Quality exclusions | Implemented | Unknown program, short/sparse/low-energy cycles |
| Tariff normalisation | Implemented | Existing tested engine |
| Profile-aware costing | Implemented | Existing tested engine |
| Green/blocked windows | Implemented | Generic HA entity inputs |
| Earliest start/latest finish | Implemented | Generic HA datetime inputs |
| Strategies and overnight policy | Implemented | Options flow |
| Program policies | Implemented | JSON options pending richer editor |
| Intent recommendations | Implemented | Now, soon, overnight, negative and greenest |
| Cost forecast/decision trace | Implemented | Native sensor attributes |
| Readiness | Implemented | Native binary sensors |
| Privacy-safe diagnostics | Implemented | No entity IDs or stored traces exported |
| Reset/recalculate | Implemented | Native buttons |
| Legacy YAML/dashboard reference | Preserved | Examples only; never loaded automatically |
| Legacy persisted-state import | Pending | Requires a deliberate user export/import path |
| Appliance command execution | Safety-blocked | Not enabled without end-to-end HA tests |
| Bosch command confirmation/audit | Pending | Must retain all legacy safety gates |
| Recovery watchdog/Repairs | Pending | Native Repairs implementation required |
| Custom dashboard/panel | Pending | Native entities work with standard dashboards |
