param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,
    [string]$ProjectName = "bo3_ported_assets",
    [string]$BlenderExe = "blender",
    [string]$ConvertedRoot = "_build\\asset_port_pipeline\\converted_zone_raw",
    [string]$GroundTruthOut = "_build\\asset_port_pipeline\\bo2_ground_truth.json",
    [string]$CompileDatasetOut = "_build\\asset_port_pipeline\\compile_dataset",
    [string]$LinkerPath = "tools\\oat\\Linker.exe",
    [string[]]$LoadZones = @("zone\\all\\common_zm.ff"),
    [string[]]$DependencyRoots = @("zone_dump\\zone_raw", "_build\\t6_asset_dump\\zone_raw"),
    [bool]$AutoResolveMissing = $true,
    [int]$MaxLinkerRetries = 2,
    [string]$ProfilesPath = "tools\\asset_port_pipeline\\conversion_profiles.json",
    [double]$DecimateRatio = 0.45,
    [int]$MaxBones = 128,
    [int]$MaxWeights = 4,
    [switch]$AutoTune,
    [switch]$RemediateFailures,
    [int]$RemediateMaxAssets = 0,
    [switch]$EnableGameplayParity,
    [string]$GameplaySource = "",
    [string]$GameplayBaselineOut = "_build\\asset_port_pipeline\\bo2_gameplay_baseline.json",
    [string]$GameplayProjectName = "bo3_gameplay_port",
    [string]$GameplayOutputRoot = "_build\\asset_port_pipeline\\converted_gameplay",
    [string]$BossProfile = "",
    [string]$BossScriptOut = "_build\\asset_port_pipeline\\generated_gsc\\boss_ported.gsc",
    [switch]$EnableMapPortPlan,
    [string]$MapSourceZoneRoot = "",
    [string]$MapSourceName = "",
    [string]$MapPlanOut = "_build\\asset_port_pipeline\\map_port_plan.json",
    [string]$MapBootstrapProject = "",
    [string]$MapBootstrapRoot = "_build\\asset_port_pipeline\\map_port_projects",
    [switch]$MapBootstrapOnlyMissing,
    [int]$MapBootstrapMaxAssets = 0,
    [switch]$MapRemediateProject,
    [int]$MapRemediateRetries = 20,
    [switch]$MapRemediatePruneUnresolved,
    [switch]$EnableScriptParity,
    [string]$ScriptSource = "",
    [string]$ScriptProfileOut = "_build\\asset_port_pipeline\\compiled_gsc_profile.json",
    [string]$ScriptStubOut = "_build\\asset_port_pipeline\\generated_gsc\\map_port_stub.gsc",
    [switch]$MapExportMeshPack,
    [string]$MapMeshPackRoot = "_build\\asset_port_pipeline\\mesh_packs",
    [string]$MapMeshPackReport = "_build\\asset_port_pipeline\\mesh_pack_export_report.json",
    [switch]$FinalizeIntegrationBundle,
    [string]$IntegrationRoot = "_build\\asset_port_pipeline\\integration_ready",
    [string]$IntegrationBundleName = "",
    [switch]$IntegrationCompile,
    [string]$IntegrationInstallZoneDir = "",
    [string]$IntegrationReport = "_build\\asset_port_pipeline\\finalize_bo2_integration_report.json",
    [switch]$SkipGroundTruth,
    [switch]$CopyGlbWithoutBlender
)

$ErrorActionPreference = "Stop"

function Invoke-PythonChecked {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    python @Args
    if ($LASTEXITCODE -ne 0) {
        throw ("Python command failed (exit " + $LASTEXITCODE + "): python " + ($Args -join " "))
    }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptRoot "..\\..")).Path
Push-Location $repoRoot

try {
    $resolvedMapProjectRoot = $null
    $resolvedMapProjectName = ""
    $resolvedMapLoadZones = @()

    if (-not $SkipGroundTruth) {
        Invoke-PythonChecked -Args @(
            "tools\asset_port_pipeline\build_bo2_ground_truth.py",
            "--roots", "_build\t6_asset_dump\zone_raw", "zone_dump\zone_raw",
            "--output", $GroundTruthOut
        )
    }

    if ($AutoTune) {
        $tuneArgs = @(
            "tools\asset_port_pipeline\auto_tune_conversion.py",
            "--input", $SourceRoot,
            "--profiles", $ProfilesPath,
            "--project-name", $ProjectName,
            "--output-root", $ConvertedRoot,
            "--workspace", "_build\asset_port_pipeline\auto_tune_workspace",
            "--blender-exe", $BlenderExe,
            "--linker", $LinkerPath
        )
        if ($LoadZones.Count -gt 0) {
            $tuneArgs += "--load-zones"
            $tuneArgs += $LoadZones
        }
        if ($AutoResolveMissing) {
            $tuneArgs += "--auto-resolve-missing"
            $tuneArgs += "--max-retries"
            $tuneArgs += $MaxLinkerRetries
            if ($DependencyRoots.Count -gt 0) {
                $tuneArgs += "--dependency-roots"
                $tuneArgs += $DependencyRoots
            }
        }
        if ($CopyGlbWithoutBlender) {
            $tuneArgs += "--copy-glb-without-blender"
        }
        Invoke-PythonChecked -Args $tuneArgs
    }
    else {
        $convertArgs = @(
            "tools\asset_port_pipeline\blender_convert.py",
            "--input", $SourceRoot,
            "--output-root", $ConvertedRoot,
            "--project-name", $ProjectName,
            "--blender-exe", $BlenderExe,
            "--decimate-ratio", $DecimateRatio,
            "--max-bones", $MaxBones,
            "--max-weights", $MaxWeights
        )
        if ($CopyGlbWithoutBlender) {
            $convertArgs += "--copy-glb-without-blender"
        }
        Invoke-PythonChecked -Args $convertArgs
    }

    $xmodelRoot = Join-Path $ConvertedRoot (Join-Path $ProjectName "xmodel")
    $datasetArgs = @(
        "tools\asset_port_pipeline\build_compile_dataset.py",
        "--xmodel-root", $xmodelRoot,
        "--output-dir", $CompileDatasetOut,
        "--linker", $LinkerPath
    )
    if ($LoadZones.Count -gt 0) {
        $datasetArgs += "--load-zones"
        $datasetArgs += $LoadZones
    }
    if ($AutoResolveMissing) {
        $datasetArgs += "--auto-resolve-missing"
        $datasetArgs += "--max-retries"
        $datasetArgs += $MaxLinkerRetries
        if ($DependencyRoots.Count -gt 0) {
            $datasetArgs += "--dependency-roots"
            $datasetArgs += $DependencyRoots
        }
    }
    Invoke-PythonChecked -Args $datasetArgs

    if ($RemediateFailures) {
        $remediateArgs = @(
            "tools\asset_port_pipeline\remediate_compile_failures.py",
            "--dataset-jsonl", (Join-Path $CompileDatasetOut "compile_dataset.jsonl"),
            "--failure-summary", (Join-Path $CompileDatasetOut "compile_failure_summary.json"),
            "--workspace", "_build\asset_port_pipeline\linker_oracle_remediation",
            "--output-dir", (Join-Path $CompileDatasetOut "remediation"),
            "--linker", $LinkerPath,
            "--max-retries", $MaxLinkerRetries
        )
        if ($LoadZones.Count -gt 0) {
            $remediateArgs += "--load-zones"
            $remediateArgs += $LoadZones
        }
        if ($DependencyRoots.Count -gt 0) {
            $remediateArgs += "--dependency-roots"
            $remediateArgs += $DependencyRoots
        }
        if ($RemediateMaxAssets -gt 0) {
            $remediateArgs += "--max-assets"
            $remediateArgs += $RemediateMaxAssets
        }
        Invoke-PythonChecked -Args $remediateArgs
    }

    if (Test-Path $GroundTruthOut) {
        Invoke-PythonChecked -Args @(
            "tools\asset_port_pipeline\validate_assets.py",
            "--baseline", $GroundTruthOut,
            "--inputs", (Join-Path $ConvertedRoot $ProjectName),
            "--type", "auto",
            "--output", "_build\asset_port_pipeline\converted_validation_report.json"
        )
    }
    else {
        Write-Warning ("Skipping validate_assets.py because baseline file was not found: " + $GroundTruthOut)
    }

    if ($EnableGameplayParity) {
        Invoke-PythonChecked -Args @(
            "tools\asset_port_pipeline\build_bo2_gameplay_baseline.py",
            "--roots", "zone_dump\zone_raw", "_build\t6_asset_dump\zone_raw",
            "--output", $GameplayBaselineOut
        )

        if ($GameplaySource -ne "") {
            Invoke-PythonChecked -Args @(
                "tools\asset_port_pipeline\translate_weapon_gameplay.py",
                "--input", $GameplaySource,
                "--baseline", $GameplayBaselineOut,
                "--output-root", $GameplayOutputRoot,
                "--project-name", $GameplayProjectName,
                "--report", "_build\asset_port_pipeline\weapon_gameplay_translation_report.json"
            )
        }
        else {
            Write-Warning "EnableGameplayParity set but GameplaySource is empty. Skipping weapon gameplay translation."
        }

        if ($BossProfile -ne "") {
            Invoke-PythonChecked -Args @(
                "tools\asset_port_pipeline\generate_boss_parity_gsc.py",
                "--profile", $BossProfile,
                "--output", $BossScriptOut,
                "--report", "_build\asset_port_pipeline\boss_parity_report.json"
            )
        }
    }

    if ($EnableMapPortPlan) {
        if ($MapSourceZoneRoot -eq "") {
            Write-Warning "EnableMapPortPlan set but MapSourceZoneRoot is empty. Skipping map parity planning."
        }
        else {
            $mapPlanArgs = @(
                "tools\asset_port_pipeline\plan_map_port.py",
                "--source-zone-root", $MapSourceZoneRoot,
                "--bo2-reference-roots", "zone_dump\zone_raw", "_build\t6_asset_dump\zone_raw",
                "--output", $MapPlanOut
            )
            if ($MapSourceName -ne "") {
                $mapPlanArgs += "--source-map"
                $mapPlanArgs += $MapSourceName
            }
            Invoke-PythonChecked -Args $mapPlanArgs

            if ($MapBootstrapProject -ne "") {
                $bootstrapReportPath = "_build\asset_port_pipeline\map_bootstrap_report.json"
                $bootstrapArgs = @(
                    "tools\asset_port_pipeline\bootstrap_map_port_project.py",
                    "--plan", $MapPlanOut,
                    "--project-name", $MapBootstrapProject,
                    "--output-root", $MapBootstrapRoot,
                    "--include-phases", "core_map", "render_assets", "gameplay_assets", "scripts",
                    "--output-report", $bootstrapReportPath
                )
                if ($MapBootstrapOnlyMissing) {
                    $bootstrapArgs += "--only-bo2-missing"
                }
                if ($MapBootstrapMaxAssets -gt 0) {
                    $bootstrapArgs += "--max-assets"
                    $bootstrapArgs += $MapBootstrapMaxAssets
                }
                Invoke-PythonChecked -Args $bootstrapArgs

                $resolvedMapProjectRoot = Join-Path $MapBootstrapRoot $MapBootstrapProject
                $resolvedMapProjectName = $MapBootstrapProject
                $resolvedMapLoadZones = @()
                if ($LoadZones.Count -gt 0) {
                    $resolvedMapLoadZones += $LoadZones
                }
                if ($MapSourceName -ne "") {
                    $sourceMapZoneBootstrap = "zone\\all\\" + $MapSourceName + ".ff"
                    if (Test-Path $sourceMapZoneBootstrap) {
                        $resolvedMapLoadZones += $sourceMapZoneBootstrap
                    }
                }
                $resolvedMapLoadZones = $resolvedMapLoadZones | Select-Object -Unique

                if ($MapRemediateProject) {
                    $mapProjectRoot = Join-Path $MapBootstrapRoot $MapBootstrapProject
                    $mapLoadZones = @()
                    if ($LoadZones.Count -gt 0) {
                        $mapLoadZones += $LoadZones
                    }
                    if ($MapSourceName -ne "") {
                        $sourceMapZone = "zone\\all\\" + $MapSourceName + ".ff"
                        if (Test-Path $sourceMapZone) {
                            $mapLoadZones += $sourceMapZone
                        }
                    }
                    $mapLoadZones = $mapLoadZones | Select-Object -Unique

                    $mapRemediateArgs = @(
                        "tools\asset_port_pipeline\remediate_map_project.py",
                        "--project-root", $mapProjectRoot,
                        "--project-name", $MapBootstrapProject,
                        "--linker", $LinkerPath,
                        "--max-retries", $MapRemediateRetries,
                        "--output", "_build\asset_port_pipeline\map_project_remediation_report.json"
                    )
                    if ($mapLoadZones.Count -gt 0) {
                        $mapRemediateArgs += "--load-zones"
                        $mapRemediateArgs += $mapLoadZones
                    }
                    if ($DependencyRoots.Count -gt 0) {
                        $mapRemediateArgs += "--dependency-roots"
                        $mapRemediateArgs += $DependencyRoots
                    }
                    if ($MapRemediatePruneUnresolved) {
                        $mapRemediateArgs += "--prune-unresolved"
                    }
                    Invoke-PythonChecked -Args $mapRemediateArgs

                    $resolvedMapLoadZones = $mapLoadZones
                }
            }
        }
    }

    if ($EnableScriptParity) {
        if ($ScriptSource -eq "") {
            if ($MapSourceZoneRoot -ne "") {
                $ScriptSource = Join-Path $MapSourceZoneRoot "aitype"
            }
        }
        if ($ScriptSource -eq "") {
            Write-Warning "EnableScriptParity set but ScriptSource is empty and no MapSourceZoneRoot fallback was available."
        }
        else {
            Invoke-PythonChecked -Args @(
                "tools\asset_port_pipeline\extract_compiled_gsc_profile.py",
                "--input", $ScriptSource,
                "--output", $ScriptProfileOut
            )
            $stubProjectName = $ProjectName
            if ($MapBootstrapProject -ne "") {
                $stubProjectName = $MapBootstrapProject
            }
            Invoke-PythonChecked -Args @(
                "tools\asset_port_pipeline\generate_bo2_script_stubs.py",
                "--profile", $ScriptProfileOut,
                "--project-name", $stubProjectName,
                "--output", $ScriptStubOut,
                "--report", "_build\asset_port_pipeline\script_stub_report.json"
            )
        }
    }

    if ($MapExportMeshPack) {
        if ([string]::IsNullOrWhiteSpace($resolvedMapProjectRoot) -or [string]::IsNullOrWhiteSpace($resolvedMapProjectName)) {
            Write-Warning "MapExportMeshPack set but no resolved map bootstrap project was available. Set -MapBootstrapProject when map planning is enabled."
        }
        else {
            Invoke-PythonChecked -Args @(
                "tools\asset_port_pipeline\export_compilable_mesh_pack.py",
                "--project-root", $resolvedMapProjectRoot,
                "--project-name", $resolvedMapProjectName,
                "--output-root", $MapMeshPackRoot,
                "--output-report", $MapMeshPackReport
            )
        }
    }

    if ($FinalizeIntegrationBundle) {
        $finalizeProjectRoot = ""
        $finalizeProjectName = ""
        $finalizeLoadZones = @()

        if (![string]::IsNullOrWhiteSpace($resolvedMapProjectRoot) -and ![string]::IsNullOrWhiteSpace($resolvedMapProjectName)) {
            $finalizeProjectRoot = $resolvedMapProjectRoot
            $finalizeProjectName = $resolvedMapProjectName
            $finalizeLoadZones = $resolvedMapLoadZones
        }
        else {
            $finalizeProjectRoot = Join-Path $ConvertedRoot $ProjectName
            $finalizeProjectName = $ProjectName
            if ($LoadZones.Count -gt 0) {
                $finalizeLoadZones += $LoadZones
            }
        }

        if ($MapSourceName -ne "") {
            $sourceMapZoneFinalize = "zone\\all\\" + $MapSourceName + ".ff"
            if (Test-Path $sourceMapZoneFinalize) {
                $finalizeLoadZones += $sourceMapZoneFinalize
            }
        }
        $finalizeLoadZones = $finalizeLoadZones | Select-Object -Unique

        $finalizeArgs = @(
            "tools\asset_port_pipeline\finalize_bo2_integration.py",
            "--project-root", $finalizeProjectRoot,
            "--project-name", $finalizeProjectName,
            "--output-root", $IntegrationRoot,
            "--output-report", $IntegrationReport
        )
        if ($IntegrationBundleName -ne "") {
            $finalizeArgs += "--bundle-name"
            $finalizeArgs += $IntegrationBundleName
        }
        if ($IntegrationCompile) {
            $finalizeArgs += "--compile"
            $finalizeArgs += "--linker"
            $finalizeArgs += $LinkerPath
            if ($finalizeLoadZones.Count -gt 0) {
                $finalizeArgs += "--load-zones"
                $finalizeArgs += $finalizeLoadZones
            }
        }
        if ($IntegrationInstallZoneDir -ne "") {
            $finalizeArgs += "--install-zone-dir"
            $finalizeArgs += $IntegrationInstallZoneDir
        }
        Invoke-PythonChecked -Args $finalizeArgs
    }

    Write-Host "Pipeline completed."
    Write-Host "Converted project root: " (Join-Path $ConvertedRoot $ProjectName)
    Write-Host "Compile dataset: " (Join-Path $CompileDatasetOut "compile_dataset.jsonl")
}
finally {
    Pop-Location
}
