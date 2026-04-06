param(
    [ValidateSet("static_pose", "donor_clone", "donor_template_static_pose", "donor_semantic_static_pose", "bo3_frames")]
    [string]$EmitMode = "bo3_frames",
    [ValidateSet("idleonly", "idlefire", "spawn")]
    [string]$AnimStage = "spawn",
    [string]$AnimSubset = "vm_zod_id_gun_first_raise,vm_zod_id_gun_pullout,vm_zod_id_gun_idle,vm_zod_id_gun_fire",
    [ValidateSet("idle_first_raise", "pullout", "fire", "combined", "putaway", "equip_hold")]
    [string]$AnimProbePhase = "combined",
    [string]$IdleAnimOverride = "",
    [string]$RaiseAnimOverride = "",
    [string]$QuickRaiseAnimOverride = "",
    [string]$FirstRaiseAnimOverride = "",
    [string]$FireAnimOverride = "",
    [string]$AnimDebugTargets = "",
    [string]$RunLabel = "",
    [switch]$ForceStockShell,
    [string]$ForcedStockShell = "c_zom_engineer_viewhands",
    [ValidateSet("custom", "base", "literal")]
    [string]$GunModelMode = "custom",
    [switch]$ForceLowHandmodel,
    [switch]$DisableStockSurvivorCarrier,
    [switch]$UseCustomIdgViewhands,
    [string]$IdleDiagBone = "",
    [string]$IdleDiagTranslate = "",
    [string]$IdleDiagFrequency = "",
    [string]$IdleStaticBone = "",
    [string]$IdleStaticTranslate = "",
    [string]$Map = "zm_transit",
    [string]$UiGametype = "zclassic",
    [string]$UiZmGamemodeGroup = "zsurvival",
    [string]$UiMapStartLocation = "town",
    [string]$GGametype = "zclassic",
    [string]$ExecCfg = "",
    [string[]]$ExtraCommands = @(),
    [switch]$ForceIdentity,
    [switch]$Launch,
    [switch]$InjectProbe,
    [ValidateSet("semantic_names", "target_weapon_names")]
    [string]$RuntimeBackend = "target_weapon_names",
    [bool]$PatchRuntimeBackendFF = $false,
    [ValidateSet("safe", "bootstrap_guard_only", "render_opacity_focus", "viewmodel_render_focus", "xanim_focus", "xanim_consumer_focus", "xanim_asset_lookup_focus", "producer_compact_override_focus", "class_family_materialization_writepath")]
    [string]$ProbeMode = "safe"
)

$ErrorActionPreference = "Stop"

$root = "Z:\Games\pluto_t6_full_game"
$buildScript = Join-Path $root "_build\build_bo3_rev_idg_probe.py"
$restartScript = Join-Path $root "tools\restart_t6_probe_cycle.ps1"
$oracleFf = Join-Path $root "zone\all\zm_prison.ff"

if (-not (Test-Path $buildScript)) {
    throw "Missing build script: $buildScript"
}

if (-not (Test-Path $restartScript)) {
    throw "Missing restart helper: $restartScript"
}

if (-not (Test-Path $oracleFf)) {
    throw "Missing xanim oracle fastfile: $oracleFf"
}

$defaultPhaseTargets = @{
    "vm_zod_id_gun_idle" = @("vm_zod_id_gun_idle")
    "vm_zod_id_gun_first_raise" = @("vm_zod_id_gun_first_raise")
    "vm_zod_id_gun_pullout" = @("vm_zod_id_gun_pullout", "vm_zod_id_gun_putaway")
    "vm_zod_id_gun_fire" = @("vm_zod_id_gun_fire")
}
if ([string]::IsNullOrWhiteSpace($AnimDebugTargets)) {
    $subsetNames = @($AnimSubset.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    $derivedTargets = New-Object System.Collections.Generic.List[string]
    $addTarget = {
        param([string]$Name)
        if (-not [string]::IsNullOrWhiteSpace($Name) -and -not $derivedTargets.Contains($Name)) {
            $derivedTargets.Add($Name)
        }
    }

    if ($subsetNames -contains "vm_zod_id_gun_idle") {
        & $addTarget $(if ([string]::IsNullOrWhiteSpace($IdleAnimOverride)) { "vm_zod_id_gun_idle" } else { $IdleAnimOverride })
    }
    if ($subsetNames -contains "vm_zod_id_gun_first_raise") {
        & $addTarget $(if ([string]::IsNullOrWhiteSpace($FirstRaiseAnimOverride)) { "vm_zod_id_gun_first_raise" } else { $FirstRaiseAnimOverride })
    }
    if ($subsetNames -contains "vm_zod_id_gun_pullout") {
        if ([string]::IsNullOrWhiteSpace($RaiseAnimOverride) -and [string]::IsNullOrWhiteSpace($QuickRaiseAnimOverride)) {
            foreach ($target in $defaultPhaseTargets["vm_zod_id_gun_pullout"]) {
                & $addTarget $target
            }
        } else {
            & $addTarget $RaiseAnimOverride
            & $addTarget $QuickRaiseAnimOverride
        }
    }
    if ($subsetNames -contains "vm_zod_id_gun_fire") {
        $fireTargets = if ([string]::IsNullOrWhiteSpace($FireAnimOverride)) { $defaultPhaseTargets["vm_zod_id_gun_fire"] } else { @($FireAnimOverride) }
        foreach ($fireTarget in $fireTargets) {
            & $addTarget $fireTarget
        }
    }

    if ($derivedTargets.Count -gt 0) {
        $AnimDebugTargets = ($derivedTargets -join ",")
    }
}

$env:ROGUE_USE_BO3_RAW_FX = "0"
$env:ROGUE_BO3_RAW_FX_STAGE = "off"
$env:ROGUE_USE_BO3_SERVANT_CLIENT_FX = "0"
$env:ROGUE_DEPLOY_TO_MOD = "0"
$env:ROGUE_DEPLOY_TO_BASE = "1"
$env:ROGUE_ALLOW_STRIPPED_SURVIVAL_FF = "0"
$env:ROGUE_SKIP_MOD_LOAD_SYNC = "0"
$env:ROGUE_SKIP_MOD_PATCH_SYNC = "0"
$env:ROGUE_SKIP_SCRIPT_SYNC = "0"
$env:ROGUE_REQUIRE_APPDATA_SYNC = "1"
$env:ROGUE_USE_FULL_ZONE_SOURCE = "1"
$env:ROGUE_USE_MAP_FULL_ZONE_SOURCE = "0"
$env:ROGUE_GUN_MODEL_MODE = $GunModelMode
$env:ROGUE_FORCE_LOW_HANDMODEL = $(if ($ForceLowHandmodel) { "1" } else { "0" })
$env:ROGUE_USE_STOCK_SURVIVOR_CARRIER = $(if ($DisableStockSurvivorCarrier) { "0" } else { "1" })
$env:ROGUE_STOCK_SURVIVOR_HANDMODEL = "c_zom_hazmat_viewhands"
$env:ROGUE_USE_CUSTOM_IDG_VIEWHANDS = $(if ($UseCustomIdgViewhands) { "1" } else { "0" })
$env:ROGUE_STUB_ZM_VIEWHANDS = "0"
$env:ROGUE_IDG_VIEW_GLB = (Join-Path $root "_build\bo3_rev_idg_weapon_only\bo3_rev_idg_weapon_only.glb")
$env:ROGUE_USE_BO3_IDG_ANIMS = "1"
$env:ROGUE_BO3_ANIM_STAGE = $AnimStage
$env:ROGUE_BO3_ANIM_SUBSET = $AnimSubset
$env:ROGUE_BO3_ANIM_EMIT_MODE = $EmitMode
$env:ROGUE_BO3_ANIM_RUNTIME_BACKEND = $RuntimeBackend
$env:ROGUE_BO3_ANIM_RUNTIME_STAGE_DONOR_ORDER = "1"
$env:ROGUE_BO3_ANIM_RUNTIME_BIND_ALIASES = "0"
$env:ROGUE_BO3_SPLIT_FIRE_RUNTIME_NAMES = "0"
$env:ROGUE_BO3_SPLIT_EQUIP_RUNTIME_NAMES = "0"
$env:ROGUE_WEAPON_IDLE_ANIM_OVERRIDE = $IdleAnimOverride
$env:ROGUE_WEAPON_RAISE_ANIM_OVERRIDE = $RaiseAnimOverride
$env:ROGUE_WEAPON_QUICK_RAISE_ANIM_OVERRIDE = $QuickRaiseAnimOverride
$env:ROGUE_WEAPON_FIRST_RAISE_ANIM_OVERRIDE = $FirstRaiseAnimOverride
$env:ROGUE_WEAPON_FIRE_ANIM_OVERRIDE = $FireAnimOverride
$env:ROGUE_BO3_ANIM_DEBUG_TARGETS = $AnimDebugTargets
$env:ROGUE_BO3_ANIM_DEBUG_TRANSLATE = "0,0,0"
$env:ROGUE_USE_REBAKED_BO3_XANIMS = "1"
$env:ROGUE_BO3_ANIM_DONOR_FF = $oracleFf
$env:ROGUE_BO3_ANIM_DONOR_ZONE = "zm_prison"
$env:ROGUE_BO3_ANIM_DONOR_ASSET = "viewmodel_minigun_t6_idle"
$env:ROGUE_EMIT_SHADOW_SEMANTIC_EXPORTS = "0"
$env:ROGUE_PATCH_RUNTIME_BACKEND_FF = $(if ($PatchRuntimeBackendFF) { "1" } else { "0" })
$env:ROGUE_NATIVE_PROBE_MODE = $ProbeMode
$env:ROGUE_ANIM_PROBE_PHASE = $AnimProbePhase
$env:ROGUE_RUN_LABEL = $RunLabel
$env:ROGUE_FORCE_STOCK_SHELL = $(if ($ForceStockShell) { "1" } else { "0" })
$env:ROGUE_FORCED_STOCK_SHELL = $ForcedStockShell
$env:ROGUE_BO3_IDLE_DIAG_BONE = $IdleDiagBone
$env:ROGUE_BO3_IDLE_DIAG_TRANSLATE = $IdleDiagTranslate
$env:ROGUE_BO3_IDLE_DIAG_FREQUENCY = $IdleDiagFrequency
$env:ROGUE_BO3_IDLE_DIAG_STATIC_BONE = $IdleStaticBone
$env:ROGUE_BO3_IDLE_DIAG_STATIC_TRANSLATE = $IdleStaticTranslate
$env:ROGUE_PROOF_CLIP_SIZE = "5"
$env:ROGUE_PROOF_START_AMMO = "25"
$env:ROGUE_PROOF_MAX_AMMO = "25"
$env:ROGUE_PROOF_FIRE_TIME = "0.75"
$env:ROGUE_PROOF_DAMAGE = "2000"
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
Write-Host "  ROGUE_BO3_SPLIT_FIRE_RUNTIME_NAMES=$($env:ROGUE_BO3_SPLIT_FIRE_RUNTIME_NAMES)"
Write-Host "  ROGUE_BO3_SPLIT_EQUIP_RUNTIME_NAMES=$($env:ROGUE_BO3_SPLIT_EQUIP_RUNTIME_NAMES)"
Write-Host "  ROGUE_WEAPON_IDLE_ANIM_OVERRIDE=$($env:ROGUE_WEAPON_IDLE_ANIM_OVERRIDE)"
Write-Host "  ROGUE_WEAPON_RAISE_ANIM_OVERRIDE=$($env:ROGUE_WEAPON_RAISE_ANIM_OVERRIDE)"
Write-Host "  ROGUE_WEAPON_QUICK_RAISE_ANIM_OVERRIDE=$($env:ROGUE_WEAPON_QUICK_RAISE_ANIM_OVERRIDE)"
Write-Host "  ROGUE_WEAPON_FIRST_RAISE_ANIM_OVERRIDE=$($env:ROGUE_WEAPON_FIRST_RAISE_ANIM_OVERRIDE)"
Write-Host "  ROGUE_WEAPON_FIRE_ANIM_OVERRIDE=$($env:ROGUE_WEAPON_FIRE_ANIM_OVERRIDE)"
Write-Host "  ROGUE_BO3_ANIM_DEBUG_TARGETS=$($env:ROGUE_BO3_ANIM_DEBUG_TARGETS)"
Write-Host "  ROGUE_BO3_ANIM_DEBUG_TRANSLATE=$($env:ROGUE_BO3_ANIM_DEBUG_TRANSLATE)"
Write-Host "  ROGUE_BO3_ANIM_DONOR_FF=$($env:ROGUE_BO3_ANIM_DONOR_FF)"
Write-Host "  ROGUE_EMIT_SHADOW_SEMANTIC_EXPORTS=$($env:ROGUE_EMIT_SHADOW_SEMANTIC_EXPORTS)"
Write-Host "  ROGUE_PATCH_RUNTIME_BACKEND_FF=$($env:ROGUE_PATCH_RUNTIME_BACKEND_FF)"
Write-Host "  ROGUE_NATIVE_PROBE_MODE=$($env:ROGUE_NATIVE_PROBE_MODE)"
Write-Host "  ROGUE_ANIM_PROBE_PHASE=$($env:ROGUE_ANIM_PROBE_PHASE)"
Write-Host "  ROGUE_RUN_LABEL=$($env:ROGUE_RUN_LABEL)"
Write-Host "  ROGUE_FORCE_STOCK_SHELL=$($env:ROGUE_FORCE_STOCK_SHELL)"
Write-Host "  ROGUE_FORCED_STOCK_SHELL=$($env:ROGUE_FORCED_STOCK_SHELL)"
Write-Host "  ROGUE_BO3_IDLE_DIAG_BONE=$($env:ROGUE_BO3_IDLE_DIAG_BONE)"
Write-Host "  ROGUE_BO3_IDLE_DIAG_TRANSLATE=$($env:ROGUE_BO3_IDLE_DIAG_TRANSLATE)"
Write-Host "  ROGUE_BO3_IDLE_DIAG_FREQUENCY=$($env:ROGUE_BO3_IDLE_DIAG_FREQUENCY)"
Write-Host "  ROGUE_BO3_IDLE_DIAG_STATIC_BONE=$($env:ROGUE_BO3_IDLE_DIAG_STATIC_BONE)"
Write-Host "  ROGUE_BO3_IDLE_DIAG_STATIC_TRANSLATE=$($env:ROGUE_BO3_IDLE_DIAG_STATIC_TRANSLATE)"
Write-Host "  ROGUE_PROOF_CLIP_SIZE=$($env:ROGUE_PROOF_CLIP_SIZE)"
Write-Host "  ROGUE_PROOF_START_AMMO=$($env:ROGUE_PROOF_START_AMMO)"
Write-Host "  ROGUE_PROOF_MAX_AMMO=$($env:ROGUE_PROOF_MAX_AMMO)"
Write-Host "  ROGUE_FORCE_LOW_HANDMODEL=$($env:ROGUE_FORCE_LOW_HANDMODEL)"
Write-Host "  ROGUE_USE_STOCK_SURVIVOR_CARRIER=$($env:ROGUE_USE_STOCK_SURVIVOR_CARRIER)"
Write-Host "  ROGUE_STOCK_SURVIVOR_HANDMODEL=$($env:ROGUE_STOCK_SURVIVOR_HANDMODEL)"
Write-Host "  ROGUE_USE_CUSTOM_IDG_VIEWHANDS=$($env:ROGUE_USE_CUSTOM_IDG_VIEWHANDS)"
Write-Host "  ROGUE_STUB_ZM_VIEWHANDS=$($env:ROGUE_STUB_ZM_VIEWHANDS)"
Write-Host "  ROGUE_IDG_VIEW_GLB=$($env:ROGUE_IDG_VIEW_GLB)"
Write-Host "  ROGUE_USE_BO3_FX_LOAD_FF=$($env:ROGUE_USE_BO3_FX_LOAD_FF)"
Write-Host "  ROGUE_SKIP_MOD_LOAD_SYNC=$($env:ROGUE_SKIP_MOD_LOAD_SYNC)"
Write-Host "  ROGUE_SKIP_SCRIPT_SYNC=$($env:ROGUE_SKIP_SCRIPT_SYNC)"
Write-Host "  ROGUE_REQUIRE_APPDATA_SYNC=$($env:ROGUE_REQUIRE_APPDATA_SYNC)"
Write-Host "  ROGUE_USE_FULL_ZONE_SOURCE=$($env:ROGUE_USE_FULL_ZONE_SOURCE)"
Write-Host "  ROGUE_USE_MAP_FULL_ZONE_SOURCE=$($env:ROGUE_USE_MAP_FULL_ZONE_SOURCE)"
Write-Host "  ROGUE_DEPLOY_TO_MOD=$($env:ROGUE_DEPLOY_TO_MOD)"
Write-Host "  ROGUE_DEPLOY_TO_BASE=$($env:ROGUE_DEPLOY_TO_BASE)"
Write-Host "  ROGUE_ALLOW_STRIPPED_SURVIVAL_FF=$($env:ROGUE_ALLOW_STRIPPED_SURVIVAL_FF)"

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
    if (-not [string]::IsNullOrWhiteSpace($Map)) {
        $restartArgs += @("-Map", $Map)
    }
    if (-not [string]::IsNullOrWhiteSpace($UiGametype)) {
        $restartArgs += @("-UiGametype", $UiGametype)
    }
    if (-not [string]::IsNullOrWhiteSpace($UiZmGamemodeGroup)) {
        $restartArgs += @("-UiZmGamemodeGroup", $UiZmGamemodeGroup)
    }
    if (-not [string]::IsNullOrWhiteSpace($UiMapStartLocation)) {
        $restartArgs += @("-UiMapStartLocation", $UiMapStartLocation)
    }
    if (-not [string]::IsNullOrWhiteSpace($GGametype)) {
        $restartArgs += @("-GGametype", $GGametype)
    }
    if (-not [string]::IsNullOrWhiteSpace($ExecCfg)) {
        $restartArgs += @("-ExecCfg", $ExecCfg)
    }
    foreach ($cmd in $ExtraCommands) {
        if (-not [string]::IsNullOrWhiteSpace($cmd)) {
            $restartArgs += @("-ExtraCommands", $cmd)
        }
    }
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
