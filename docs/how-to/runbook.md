# BO3 Rev Runbook

This is the operational loop for single-variable BO3 Rev iteration.

## 1. Start clean
```powershell
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode clean
powershell -ExecutionPolicy Bypass -File "_build/runtime_reset.ps1" -Mode dev -DevMod "bo3_rev"
```

## 2. Choose one variable class only
Per run, change one class:
1. donor shell
2. rig/fit transform
3. material/image path
4. animation alias mapping
5. GSC logic
6. runtime lane/deploy behavior

If a run changes more than one class, it is not diagnostic.

## 3. Build
Default working case:

```powershell
python _build/run_bo3_rev_probe_case.py mg08_v2_bo3_weapon_only
```

## 4. Restart
If FF/IPAK/xmodel/materials changed, do a full game restart.

## 5. Verify build provenance
Before judging the result, confirm:
- in-game build tag
- rendered raw script
- build report

## 6. Record the result by category
For each run, record:
- build tag
- donor shell
- what changed
- what failed
- what the failure proved

Recommended categories:
- registration
- donor-shell composition
- bone budget
- material/IPAK
- fit/origin
- gameplay logic
- FX/presentation

## 7. Known-good current baseline
The known-good starting point is:
- case: `mg08_v2_bo3_weapon_only`
- donor shell: `mg08_zm`
- custom model loads
- pull/kill logic works
- demo commands work

If a new experiment breaks the baseline, return to this case first.
