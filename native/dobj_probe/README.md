# DObj Probe

Debug-only x86 client hook for logging the runtime stack at the BO2/T6 error path that emits:

`dobj for xmodel '%s' has more than %i bones (see console for details)`

## What it does

- Scans the main game module for the target error format string.
- Finds x86 `push imm32` references to that string in `.text`.
- Detours those sites.
- Logs stack slots and raw backtrace addresses when the error path is hit.

This is intended to answer: what does the engine actually have on the stack right before the `>160 bones` failure?

## Build

```powershell
powershell -ExecutionPolicy Bypass -File native/dobj_probe/build_x86.ps1
```

Outputs:

- `native/dobj_probe/bin/x86/Release/dobj_probe_hook_<timestamp>.dll`
- `native/dobj_probe/bin/x86/Release/dobj_probe_injector.exe`

## Inject

Inject into the actual BO2/T6 game process, not the Plutonium bootstrapper:

```powershell
powershell -ExecutionPolicy Bypass -File native/dobj_probe/inject_latest.ps1 -ProcessName t6zm.exe
```

Or by PID:

```powershell
powershell -ExecutionPolicy Bypass -File native/dobj_probe/inject_latest.ps1 -TargetPid 12345
```

Or start the injector first and let it wait for the game:

```powershell
powershell -ExecutionPolicy Bypass -File native/dobj_probe/inject_latest.ps1 -ProcessName t6zm.exe -Wait
```

## Log

The DLL writes:

- `native/dobj_probe/bin/x86/Release/dobj_probe.log`

Look for:

- `Installed hook`
- `bone_error_ref_hit`
- `stack ...`
- `stack_str[...]`
- `backtrace[...]`

## Limits

- This is x86-only.
- It logs the error-path stack, not a fully symbolized DObj graph.
- Raw backtrace addresses still need reverse-engineering to map to exact functions.
