param(
    [ValidateSet("static_pose", "donor_clone", "donor_template_static_pose", "donor_semantic_static_pose", "bo3_frames")]
    [string]$EmitMode = "bo3_frames",
    [ValidateSet("idlefire", "spawn")]
    [string]$AnimStage = "spawn",
    [switch]$ForceIdentity,
    [switch]$Launch,
    [switch]$InjectProbe,
    [ValidateSet("safe", "render_opacity_focus", "xanim_focus")]
    [string]$ProbeMode = "safe"
)

$ErrorActionPreference = "Stop"

$root = "Z:\Games\pluto_t6_full_game"
$buildScript = Join-Path $root "_build\build_bo3_rev_idg_probe.py"
$restartScript = Join-Path $root "tools\restart_t6_probe_cycle.ps1"
$oracleFf = Join-Path $root "zone\all\so_zsurvival_zm_transit.ff"

if (-not (Test-Path $buildScript)) {
    throw "Missing build script: $buildScript"
}

if (-not (Test-Path $restartScript)) {
    throw "Missing restart helper: $restartScript"
}

if (-not (Test-Path $oracleFf)) {
    throw "Missing xanim oracle fastfile: $oracleFf"
}

$animSubset = "vm_zod_id_gun_first_raise,vm_zod_id_gun_idle,vm_zod_id_gun_fire"

$env:ROGUE_USE_BO3_RAW_FX = "0"
$env:ROGUE_BO3_RAW_FX_STAGE = "off"
$env:ROGUE_USE_BO3_SERVANT_CLIENT_FX = "0"
$env:ROGUE_DEPLOY_TO_MOD = "1"
$env:ROGUE_DEPLOY_TO_BASE = "0"
$env:ROGUE_ALLOW_STRIPPED_SURVIVAL_FF = "1"
$env:ROGUE_SKIP_MOD_LOAD_SYNC = "0"
$env:ROGUE_SKIP_MOD_PATCH_SYNC = "1"
$env:ROGUE_USE_BO3_IDG_ANIMS = "1"
$env:ROGUE_BO3_ANIM_STAGE = $AnimStage
$env:ROGUE_BO3_ANIM_SUBSET = $animSubset
$env:ROGUE_BO3_ANIM_EMIT_MODE = $EmitMode
$env:ROGUE_BO3_ANIM_RUNTIME_BACKEND = "target_weapon_names"
$env:ROGUE_BO3_ANIM_RUNTIME_STAGE_DONOR_ORDER = "1"
$env:ROGUE_BO3_ANIM_RUNTIME_BIND_ALIASES = "0"
$env:ROGUE_USE_REBAKED_BO3_XANIMS = "1"
$env:ROGUE_BO3_ANIM_DONOR_FF = $oracleFf
$env:ROGUE_BO3_ANIM_DONOR_ZONE = "so_zsurvival_zm_transit"
$env:ROGUE_BO3_ANIM_DONOR_ASSET = "viewmodel_zomb_mg08_idle"
$env:ROGUE_PATCH_RUNTIME_BACKEND_FF = "1"
$env:ROGUE_USE_BO3_FX_LOAD_FF = "0"
$env:ROGUE_BO3_FX_LOAD_ZONE = "mod_load"
$env:ROGUE_INCLUDE_FX_DEBUG_PROBES = "0"
$env:ROGUE_PROBE_ONLY_FAST_PATH = "0"
$env:ROGUE_CLIENT_FFPROBE_ASSET = ""
$env:ROGUE_SERVANT_FX_SCOPE = "full"
$env:ROGUE_SERVANT_VORTEX_LAYER_MODE = "all"
$env:ROGUE_PHOSPHOROUS_RENDER_MODE = "safe_alpha"

if ($ForceIdentity) {
    $env:ROGUE_BO3_ANIM_FORCE_IDENTITY = "1"
} else {
    $env:ROGUE_BO3_ANIM_FORCE_IDENTITY = "0"
}

Write-Host "Building coherent minimal Servant animation lane..."
Write-Host "  ROGUE_USE_BO3_RAW_FX=$($env:ROGUE_USE_BO3_RAW_FX)"
Write-Host "  ROGUE_BO3_RAW_FX_STAGE=$($env:ROGUE_BO3_RAW_FX_STAGE)"
Write-Host "  ROGUE_USE_BO3_SERVANT_CLIENT_FX=$($env:ROGUE_USE_BO3_SERVANT_CLIENT_FX)"
Write-Host "  ROGUE_USE_BO3_IDG_ANIMS=$($env:ROGUE_USE_BO3_IDG_ANIMS)"
Write-Host "  ROGUE_BO3_ANIM_STAGE=$($env:ROGUE_BO3_ANIM_STAGE)"
Write-Host "  ROGUE_BO3_ANIM_SUBSET=$($env:ROGUE_BO3_ANIM_SUBSET)"
Write-Host "  ROGUE_BO3_ANIM_EMIT_MODE=$($env:ROGUE_BO3_ANIM_EMIT_MODE)"
Write-Host "  ROGUE_BO3_ANIM_RUNTIME_BACKEND=$($env:ROGUE_BO3_ANIM_RUNTIME_BACKEND)"
Write-Host "  ROGUE_BO3_ANIM_RUNTIME_BIND_ALIASES=$($env:ROGUE_BO3_ANIM_RUNTIME_BIND_ALIASES)"
Write-Host "  ROGUE_BO3_ANIM_DONOR_FF=$($env:ROGUE_BO3_ANIM_DONOR_FF)"
Write-Host "  ROGUE_USE_BO3_FX_LOAD_FF=$($env:ROGUE_USE_BO3_FX_LOAD_FF)"

python $buildScript
if ($LASTEXITCODE -ne 0) {
    throw "Minimal Servant animation build failed with exit code $LASTEXITCODE"
}

$staleClientScriptSources = @(
    (Join-Path $root "mods\\bo3_rev\\clientscripts\\mp\\zm_transit.csc"),
    (Join-Path $root "mods\\bo3_rev\\clientscripts\\mp\\_visionset_mgr.csc"),
    (Join-Path $root "mods\\bo3_rev\\clientscripts\\mp\\zombies\\_bo3_rev_servant_fx_v3.csc")
)
foreach ($stale in $staleClientScriptSources) {
    if (Test-Path $stale) {
        Remove-Item -Path $stale -Force
        Write-Host "Removed stale loose clientscript source: $stale"
    }
}

$restartArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", $restartScript,
    "-ModOnly"
)
if ($Launch) {
    $restartArgs += "-Launch"
}
if ($InjectProbe) {
    $restartArgs += "-InjectProbe"
    $restartArgs += @("-ProbeMode", $ProbeMode)
}

Write-Host "Syncing runtime artifacts..."
powershell @restartArgs
if ($LASTEXITCODE -ne 0) {
    throw "Restart/sync helper failed with exit code $LASTEXITCODE"
}
