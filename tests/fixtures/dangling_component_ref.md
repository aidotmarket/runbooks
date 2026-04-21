# Dangling Component Ref

## §C. Architecture & Interactions

| Component | Component Entry Point | State Stores | Integrates With | Notes |
|---|---|---|---|---|
| CLI | `infisical/cli.py:main` | local config, ephemeral stdout buffer | Infisical API, operator shell | Primary operator entry point for read and audit flows. |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: GhostCLI
  root_cause: Operator supplied an incorrect path or environment flag during retrieval.
  repair_entry_point: infisical/cli.py:resolve_secret_target
  change_pattern: Normalize path and environment arguments before issuing the read call.
  rollback_procedure: Revert the normalization change and restore the previous flag parser.
  integrity_check: Re-run the failing retrieval and confirm the expected secret is returned.
```
