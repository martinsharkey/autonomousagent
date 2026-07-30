"""Dependency Guardian — keeps the council's toolchain current and secure.

Responsibilities:
- Track all dependencies and their versions
- Detect stale/outdated packages
- Verify compatibility before upgrades  
- Synthesize new tools from fragments when existing ones fail
- Maintain a tool registry with health scores
- Auto-propose dependency bumps as mutations (only if tests pass)

Philosophy: If an open-source tool no longer meets needs, stitch fragments
of other tools together to build better, more advanced tools.
"""

from __future__ import annotations

import os
import re
import json
import subprocess
import importlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


TOOL_REGISTRY_FILE = "evolution/tool_registry.json"
DEPENDENCY_REPORT_FILE = "evolution/dependency_report.json"


class DependencyGuardian:
    """Manages dependencies, version freshness, and tool synthesis."""

    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root)
        self.requirements_file = self.repo_root / "requirements.txt"
        self.tool_registry = self._load_tool_registry()

    def audit_dependencies(self) -> Dict[str, Any]:
        """Full audit of all dependencies — versions, staleness, conflicts."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": [],
            "stale_count": 0,
            "vulnerable_count": 0,
            "import_errors": [],
            "recommendations": [],
        }

        # Parse requirements.txt
        deps = self._parse_requirements()
        
        for dep in deps:
            dep_info = self._check_dependency(dep)
            report["dependencies"].append(dep_info)
            if dep_info.get("stale"):
                report["stale_count"] += 1
            if dep_info.get("vulnerable"):
                report["vulnerable_count"] += 1

        # Check for import errors (packages listed but not importable)
        report["import_errors"] = self._check_import_health(deps)

        # Generate recommendations
        report["recommendations"] = self._generate_upgrade_plan(report)
        
        self._save_report(report)
        return report

    def _parse_requirements(self) -> List[Dict[str, str]]:
        """Parse requirements.txt into structured list."""
        deps = []
        if not self.requirements_file.exists():
            return deps

        content = self.requirements_file.read_text()
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            
            # Parse package==version, package>=version, package
            match = re.match(r'^([a-zA-Z0-9_-]+)\s*([><=!~]+)?\s*(.+)?$', line)
            if match:
                deps.append({
                    "name": match.group(1),
                    "constraint": match.group(2) or "",
                    "version": match.group(3) or "any",
                    "raw": line,
                })

        return deps

    def _check_dependency(self, dep: Dict[str, str]) -> Dict[str, Any]:
        """Check a single dependency for version, staleness, importability."""
        info = {
            "name": dep["name"],
            "pinned_version": dep["version"],
            "installed_version": None,
            "latest_version": None,
            "stale": False,
            "vulnerable": False,
            "importable": False,
        }

        # Check installed version
        try:
            result = subprocess.run(
                ["pip", "show", dep["name"]],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Version:"):
                        info["installed_version"] = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

        # Try importing
        import_name = dep["name"].replace("-", "_").lower()
        try:
            importlib.import_module(import_name)
            info["importable"] = True
        except (ImportError, ModuleNotFoundError):
            # Some packages have different import names
            info["importable"] = False

        # Check latest version via pip index (if available)
        try:
            result = subprocess.run(
                ["pip", "index", "versions", dep["name"]],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                # Parse "Available versions: x.y.z, ..."
                match = re.search(r'Available versions:\s*(.+)', result.stdout)
                if match:
                    versions = match.group(1).split(",")
                    if versions:
                        info["latest_version"] = versions[0].strip()
                        if info["installed_version"] and info["latest_version"]:
                            info["stale"] = info["installed_version"] != info["latest_version"]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return info

    def _check_import_health(self, deps: List[Dict[str, str]]) -> List[str]:
        """Check which declared dependencies can't actually be imported."""
        errors = []
        for dep in deps:
            import_name = dep["name"].replace("-", "_").lower()
            try:
                importlib.import_module(import_name)
            except (ImportError, ModuleNotFoundError):
                errors.append(dep["name"])
        return errors

    def _generate_upgrade_plan(self, report: Dict[str, Any]) -> List[str]:
        """Generate prioritized upgrade recommendations."""
        recs = []
        
        stale = [d for d in report["dependencies"] if d.get("stale")]
        if stale:
            # Prioritize security-critical packages
            security_pkgs = {"cryptography", "urllib3", "requests", "certifi", "pip"}
            critical_stale = [d for d in stale if d["name"] in security_pkgs]
            
            if critical_stale:
                names = ", ".join(d["name"] for d in critical_stale)
                recs.append(f"PRIORITY: Upgrade security packages: {names}")
            
            if len(stale) > 3:
                recs.append(f"{len(stale)} packages are outdated — run `pip install --upgrade` batch")

        if report["import_errors"]:
            recs.append(f"Install missing: pip install {' '.join(report['import_errors'])}")

        return recs

    # --- Tool Synthesis ---

    def register_tool(self, name: str, module_path: str, capabilities: List[str],
                     health_score: float = 1.0) -> None:
        """Register a tool in the council's tool registry."""
        self.tool_registry[name] = {
            "module_path": module_path,
            "capabilities": capabilities,
            "health_score": health_score,
            "registered_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "use_count": 0,
            "failures": 0,
        }
        self._save_tool_registry()

    def report_tool_failure(self, name: str, error: str) -> None:
        """Record a tool failure — triggers synthesis if threshold exceeded."""
        if name in self.tool_registry:
            tool = self.tool_registry[name]
            tool["failures"] = tool.get("failures", 0) + 1
            tool["last_error"] = error
            tool["last_failure"] = datetime.utcnow().isoformat()
            
            # Degrade health score
            tool["health_score"] = max(0, tool.get("health_score", 1.0) - 0.2)
            self._save_tool_registry()

    def report_tool_success(self, name: str) -> None:
        """Record successful tool use."""
        if name in self.tool_registry:
            tool = self.tool_registry[name]
            tool["use_count"] = tool.get("use_count", 0) + 1
            tool["last_used"] = datetime.utcnow().isoformat()
            # Slowly recover health
            tool["health_score"] = min(1.0, tool.get("health_score", 1.0) + 0.05)
            self._save_tool_registry()

    def get_failing_tools(self) -> List[Dict[str, Any]]:
        """Get tools below health threshold that may need replacement."""
        failing = []
        for name, tool in self.tool_registry.items():
            if tool.get("health_score", 1.0) < 0.4:
                failing.append({"name": name, **tool})
        return failing

    def propose_tool_synthesis(self, failing_tool: str) -> Optional[Dict[str, Any]]:
        """Generate a mutation proposal to synthesize a replacement tool.
        
        Strategy: Identify the capabilities needed, find partial solutions
        in existing tools, and propose combining them.
        """
        if failing_tool not in self.tool_registry:
            return None

        tool = self.tool_registry[failing_tool]
        capabilities = tool.get("capabilities", [])
        
        # Find other tools that partially cover these capabilities
        alternatives = []
        for name, other_tool in self.tool_registry.items():
            if name == failing_tool:
                continue
            overlap = set(other_tool.get("capabilities", [])) & set(capabilities)
            if overlap:
                alternatives.append({
                    "name": name,
                    "overlapping_capabilities": list(overlap),
                    "health": other_tool.get("health_score", 0),
                })

        return {
            "description": f"Synthesize replacement for failing tool: {failing_tool}",
            "rationale": (
                f"Tool '{failing_tool}' has degraded to health={tool.get('health_score', 0):.1f} "
                f"with {tool.get('failures', 0)} failures. "
                f"Capabilities needed: {capabilities}. "
                f"Alternative fragments available: {[a['name'] for a in alternatives]}"
            ),
            "mutation_type": "tool_creation",
            "risk_level": "medium",
            "proposed_changes": {
                "action": "synthesize_replacement",
                "failing_tool": failing_tool,
                "required_capabilities": capabilities,
                "fragment_sources": alternatives,
            },
            "expected_improvement": 0.4,
        }

    def get_tool_health_summary(self) -> str:
        """Summary for agent prompt injection."""
        total = len(self.tool_registry)
        healthy = sum(1 for t in self.tool_registry.values() if t.get("health_score", 0) >= 0.7)
        failing = sum(1 for t in self.tool_registry.values() if t.get("health_score", 0) < 0.4)
        
        return f"Tools: {total} registered, {healthy} healthy, {failing} failing"

    def _load_tool_registry(self) -> Dict[str, Any]:
        try:
            if os.path.exists(TOOL_REGISTRY_FILE):
                with open(TOOL_REGISTRY_FILE) as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_tool_registry(self) -> None:
        try:
            os.makedirs(os.path.dirname(TOOL_REGISTRY_FILE), exist_ok=True)
            with open(TOOL_REGISTRY_FILE, "w") as f:
                json.dump(self.tool_registry, f, indent=2)
        except Exception:
            pass

    def _save_report(self, report: Dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(DEPENDENCY_REPORT_FILE), exist_ok=True)
            with open(DEPENDENCY_REPORT_FILE, "w") as f:
                json.dump(report, f, indent=2)
        except Exception:
            pass


# Singleton
_guardian: Optional[DependencyGuardian] = None


def get_dependency_guardian() -> DependencyGuardian:
    global _guardian
    if _guardian is None:
        _guardian = DependencyGuardian()
    return _guardian
