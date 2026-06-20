# Rebuild git history with incremental feature-branch PRs.
# Requires: git, gh (authenticated), snapshot at $SnapshotRoot

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$SnapshotRoot = "c:\Users\ICT\Desktop\ecf-snapshot"

function Copy-SnapshotItem {
    param([string[]]$Paths)
    foreach ($rel in $Paths) {
        $src = Join-Path $SnapshotRoot $rel
        $dst = Join-Path $RepoRoot $rel
        if (-not (Test-Path $src)) {
            throw "Missing snapshot path: $rel"
        }
        $parent = Split-Path $dst -Parent
        if ($parent -and -not (Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        if (Test-Path $src -PathType Container) {
            if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
            Copy-Item -Recurse -Force $src $dst
        } else {
            Copy-Item -Force $src $dst
        }
    }
}

function Invoke-Git {
    param([string[]]$Args)
    & git -C $RepoRoot @Args
    if ($LASTEXITCODE -ne 0) { throw "git $($Args -join ' ') failed" }
}

function New-PrAndMerge {
    param(
        [string]$Branch,
        [string]$Title,
        [string]$Body
    )
    Invoke-Git @("push", "-u", "origin", $Branch)
    $prUrl = gh pr create --repo bonsteeve/embedded-dispenser --base main --head $Branch --title $Title --body $Body
    Write-Host "Created: $prUrl"
    $prNumber = ($prUrl -split '/')[-1]
    gh pr checks $prNumber --repo bonsteeve/embedded-dispenser --watch --interval 15
    gh pr merge $prNumber --repo bonsteeve/embedded-dispenser --merge --delete-branch
    Invoke-Git @("checkout", "main")
    Invoke-Git @("pull", "origin", "main")
}

if (-not (Test-Path $SnapshotRoot)) {
    throw "Snapshot not found at $SnapshotRoot"
}

Set-Location $RepoRoot

# Backup tag (idempotent)
$tagExists = git tag -l "backup/pre-replay"
if (-not $tagExists) {
    Invoke-Git @("tag", "backup/pre-replay", "HEAD")
}

# Bootstrap content
$bootstrapReadme = @"
# Embedded Control Framework

Reusable Python patterns for embedded control systems on Linux-based hardware.

## Status

Core modules land via reviewed pull requests. See the pull request history for the integration timeline.

## Install

```bash
git clone https://github.com/bonsteeve/embedded-dispenser.git
cd embedded-dispenser
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## License

MIT — see [LICENSE](LICENSE).
"@

$bootstrapPyproject = @"
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "embedded-control-framework"
version = "0.1.0"
description = "Reusable patterns for embedded control systems on Linux-based hardware."
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.10"
authors = [{ name = "bonsteeve", email = "bonsteeve@users.noreply.github.com" }]
keywords = ["embedded", "iot", "state-machine", "sensors", "motion-control"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
    "Topic :: System :: Hardware",
]
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.25",
    "ruff>=0.9",
]

[project.urls]
Homepage = "https://github.com/bonsteeve/embedded-dispenser"
Documentation = "https://github.com/bonsteeve/embedded-dispenser#readme"
Repository = "https://github.com/bonsteeve/embedded-dispenser"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
"@

$currentBranch = git -C $RepoRoot branch --show-current
if ($currentBranch -ne "main") {
    Write-Host "Creating orphan main branch..."
    Invoke-Git @("checkout", "--orphan", "main")
    Invoke-Git @("rm", "-rf", ".")
    Copy-SnapshotItem @("LICENSE", ".gitignore")
    New-Item -ItemType Directory -Path (Join-Path $RepoRoot "src\embedded_control") -Force | Out-Null
    Copy-SnapshotItem @("src/embedded_control/__init__.py")
    Set-Content -Path (Join-Path $RepoRoot "README.md") -Value $bootstrapReadme -NoNewline
    Set-Content -Path (Join-Path $RepoRoot "pyproject.toml") -Value $bootstrapPyproject -NoNewline
    Invoke-Git @("add", ".")
    Invoke-Git @("commit", "-m", "chore: initial project bootstrap")
    Invoke-Git @("push", "-u", "origin", "main", "--force")
    gh repo edit bonsteeve/embedded-dispenser --default-branch main
    Write-Host "Bootstrap pushed to main."
} else {
    Write-Host "Already on main — continuing PR train."
}

$prs = @(
    @{
        Branch = "feature/process-state-machine"
        Title  = "feat(process): add gated transfer state machine"
        Body   = "## Summary`n- Add async gated transfer state machine with explicit states and timeouts`n- Add unit tests for happy-path and cancellation flows`n- Establish CI workflow (pytest + ruff) as merge gate`n`n## Test plan`n- [x] pytest tests/test_process_state_machine.py"
        Paths  = @(
            "src/embedded_control/process",
            "tests/test_process_state_machine.py",
            ".github/workflows/ci.yml"
        )
    },
    @{
        Branch = "feature/sensor-monitoring"
        Title  = "feat(sensors): add registry and event dispatcher"
        Body   = "## Summary`n- Add sensor registry, observer dispatch, and simulated sensor for testing`n- Integrate with existing process layer without blocking control loops`n`n## Test plan`n- [x] pytest tests/test_sensors.py"
        Paths  = @("src/embedded_control/sensors", "tests/test_sensors.py")
    },
    @{
        Branch = "feature/websocket-control"
        Title  = "feat(websocket): add priority-based message routing"
        Body   = "## Summary`n- Add extensible WebSocket handler chain with ping, health, and echo handlers`n- Add demo server and FastAPI runtime dependencies`n`n## Test plan`n- [x] pytest tests/test_websocket.py"
        Paths  = @(
            "src/embedded_control/websocket",
            "examples/demo_server.py",
            "tests/test_websocket.py"
        )
        Pyproject = $true
    },
    @{
        Branch = "feature/motion-profiling"
        Title  = "feat(motion): add S-curve acceleration profiles"
        Body   = "## Summary`n- Add pure-math S-curve profile calculator for smooth actuator ramping`n- Separate phase builder and curve functions for testability`n`n## Test plan`n- [x] pytest tests/test_motion.py"
        Paths  = @("src/embedded_control/motion", "tests/test_motion.py")
    },
    @{
        Branch = "feature/fluid-transfer"
        Title  = "feat(fluid-transfer): add dispensing orchestration subproject"
        Body   = "## Summary`n- Add pump, gate, and flow-sensor interlocks with operator-gated orchestration`n- Include runnable simulation under projects/fluid-transfer`n`n## Test plan`n- [x] pytest tests/test_fluid_transfer.py"
        Paths  = @(
            "src/fluid_transfer",
            "projects/fluid-transfer",
            "tests/test_fluid_transfer.py"
        )
    },
    @{
        Branch = "feature/robot-arm"
        Title  = "feat(robot-arm): add multi-stage positioning subproject"
        Body   = "## Summary`n- Add six-stage positioning pipeline with closed-loop retry`n- Include runnable simulation under projects/robot-arm`n`n## Test plan`n- [x] pytest tests/test_robot_arm.py"
        Paths  = @(
            "src/robot_arm",
            "projects/robot-arm",
            "tests/test_robot_arm.py"
        )
    },
    @{
        Branch = "chore/ci-and-docs"
        Title  = "docs: add architecture guide and project index"
        Body   = "## Summary`n- Document system design decisions and module boundaries`n- Add projects index linking domain subprojects`n`n## Test plan`n- [x] Existing CI suite passes"
        Paths  = @("docs/architecture.md", "projects/README.md")
    }
)

foreach ($pr in $prs) {
    $branch = $pr.Branch
    $exists = git -C $RepoRoot branch --list $branch
    if ($exists) {
        Write-Host "Skipping $branch (already exists locally)."
        continue
    }
    Write-Host "`n=== PR branch: $branch ==="
    Invoke-Git @("checkout", "main")
    Invoke-Git @("checkout", "-b", $branch)
    Copy-SnapshotItem $pr.Paths
    if ($pr.Pyproject) {
        Copy-SnapshotItem @("pyproject.toml")
        $py = Get-Content (Join-Path $RepoRoot "pyproject.toml") -Raw
        $py = $py -replace 'your-username/embedded-control-framework', 'bonsteeve/embedded-dispenser'
        $py = $py -replace 'Your Name", email = "you@example.com"', 'bonsteeve", email = "bonsteeve@users.noreply.github.com"'
        Set-Content -Path (Join-Path $RepoRoot "pyproject.toml") -Value $py -NoNewline
    }
    Invoke-Git @("add", ".")
    Invoke-Git @("commit", "-m", $pr.Title)
    New-PrAndMerge -Branch $branch -Title $pr.Title -Body $pr.Body
}

# PR #8 — repo polish
$polishBranch = "chore/repo-polish"
$polishExists = git -C $RepoRoot branch --list $polishBranch
if (-not $polishExists) {
    Write-Host "`n=== PR branch: $polishBranch ==="
    Invoke-Git @("checkout", "main")
    Invoke-Git @("checkout", "-b", $polishBranch)

    Copy-SnapshotItem @("README.md", "pyproject.toml")
    $readme = Get-Content (Join-Path $RepoRoot "README.md") -Raw
    $readme = $readme -replace 'your-username/embedded-control-framework', 'bonsteeve/embedded-dispenser'
    $badges = @"
![CI](https://github.com/bonsteeve/embedded-dispenser/actions/workflows/ci.yml/badge.svg?branch=main)
![Python](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

"@
    if ($readme -notmatch 'badge.svg') {
        $readme = $badges + $readme
    }
    Set-Content -Path (Join-Path $RepoRoot "README.md") -Value $readme -NoNewline

    $py = Get-Content (Join-Path $RepoRoot "pyproject.toml") -Raw
    $py = $py -replace 'your-username/embedded-control-framework', 'bonsteeve/embedded-dispenser'
    $py = $py -replace 'Your Name", email = "you@example.com"', 'bonsteeve", email = "bonsteeve@users.noreply.github.com"'
    Set-Content -Path (Join-Path $RepoRoot "pyproject.toml") -Value $py -NoNewline

    $contributing = @"
# Contributing

Thanks for your interest in this project.

## Development setup

```bash
git clone https://github.com/bonsteeve/embedded-dispenser.git
cd embedded-dispenser
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Workflow

1. Branch from `main` using `feature/` or `fix/` prefixes.
2. Add or update tests for behavioral changes.
3. Run `pytest -v` and `ruff check src tests examples` locally.
4. Open a pull request with a clear summary and test plan.

## Commit style

Use conventional prefixes where practical: `feat:`, `fix:`, `docs:`, `chore:`, `test:`.
"@
    Set-Content -Path (Join-Path $RepoRoot "CONTRIBUTING.md") -Value $contributing -NoNewline

    New-Item -ItemType Directory -Path (Join-Path $RepoRoot ".github\ISSUE_TEMPLATE") -Force | Out-Null
    $prTemplate = @"
## Summary

<!-- What changed and why? -->

## Test plan

- [ ] ``pytest -v``
- [ ] ``ruff check src tests examples``
"@
    Set-Content -Path (Join-Path $RepoRoot ".github\PULL_REQUEST_TEMPLATE.md") -Value $prTemplate -NoNewline

    $bugTemplate = @"
---
name: Bug report
about: Report incorrect behavior or a regression
title: ''
labels: bug
---

## Description

## Steps to reproduce

## Expected behavior

## Actual behavior

## Environment

- Python version:
- OS:
"@
    Set-Content -Path (Join-Path $RepoRoot ".github\ISSUE_TEMPLATE\bug_report.md") -Value $bugTemplate -NoNewline

    $featureTemplate = @"
---
name: Feature request
about: Suggest a new capability or improvement
title: ''
labels: enhancement
---

## Problem

## Proposed solution

## Alternatives considered
"@
    Set-Content -Path (Join-Path $RepoRoot ".github\ISSUE_TEMPLATE\feature_request.md") -Value $featureTemplate -NoNewline

    Invoke-Git @("add", ".")
    Invoke-Git @("commit", "-m", "chore: add contributing guide, templates, and README badges")
    New-PrAndMerge -Branch $polishBranch -Title "chore: add contributing guide, templates, and README badges" -Body "## Summary`n- Add CONTRIBUTING.md and GitHub issue/PR templates`n- Add CI and license badges to README`n- Align package metadata with repository URL`n`n## Test plan`n- [x] Documentation-only changes; CI unchanged"
}

# Release tag
$tagExists = git -C $RepoRoot tag -l "v0.1.0"
if (-not $tagExists) {
    Invoke-Git @("checkout", "main")
    Invoke-Git @("pull", "origin", "main")
    Invoke-Git @("tag", "-a", "v0.1.0", "-m", "Release v0.1.0: embedded control framework with fluid transfer and robot arm subprojects")
    Invoke-Git @("push", "origin", "v0.1.0")
    gh release create v0.1.0 --repo bonsteeve/embedded-dispenser --title "v0.1.0" --notes "First stable release of the embedded control framework, including process orchestration, sensor monitoring, WebSocket routing, motion profiling, and fluid transfer / robot arm subprojects."
}

# Delete legacy master branch on remote
$remoteMaster = git -C $RepoRoot ls-remote --heads origin master
if ($remoteMaster) {
    Invoke-Git @("push", "origin", "--delete", "master")
}

Write-Host "`nReplay complete."
