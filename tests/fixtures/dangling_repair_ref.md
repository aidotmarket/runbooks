# Dangling Repair Ref

## §F. Isolate

| ID | Symptom | Probable Causes | Verification Procedure | Repair Ref | Confidence |
|---|---|---|---|---|---|
| F-01 | "secret not found" in a prod retrieval flow | path typo, wrong environment, missing sync | Run `infisical secrets list` for the reported path and compare prod versus staging | §G-99 | CONFIRMED |

## §G. Repair

```yaml repair
- id: G-01
  symptom_ref: F-01
  component_ref: CLI
  root_cause: Operator supplied an incorrect path or environment flag during retrieval.
  repair_entry_point: infisical/cli.py:resolve_secret_target
  change_pattern: Normalize path and environment arguments before issuing the read call.
  rollback_procedure: Revert the normalization change and restore the previous flag parser.
  integrity_check: Re-run the failing retrieval and confirm the expected secret is returned.
```
