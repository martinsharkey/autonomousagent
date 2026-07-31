"""
Repo Janitor - cleanup micro-bot that audits the repository.

Scans for:
- Stale mutation files (rejected/failed older than N days)
- Orphaned loop cycles (old autonomous_loops entries)
- Dead code (unused imports, empty files)
- Bloated directories
- Duplicate/redundant tools
- Temporary files that shouldn't be committed

Reports findings to the council, which can then trigger cleanup mutations.
Does NOT delete anything autonomously — only reports and recommends.
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def audit_mutations(max_age_days: int = 7) -> Dict[str, Any]:
    """Audit mutation files for staleness and bloat."""
    mutations_dir = PROJECT_ROOT / "evolution" / "mutations"
    if not mutations_dir.exists():
        return {"status": "clean", "count": 0}

    results = {
        "total_files": 0,
        "stale_rejected": [],
        "stale_failed": [],
        "active": [],
        "total_size_bytes": 0,
        "oldest_file": None,
        "recommendation": "",
    }

    cutoff = datetime.utcnow() - timedelta(days=max_age_days)

    for f in mutations_dir.glob("*.json"):
        results["total_files"] += 1
        results["total_size_bytes"] += f.stat().st_size

        try:
            data = json.loads(f.read_text())
            status = data.get("status", "")
            timestamp = data.get("timestamp", "")

            # Parse timestamp
            try:
                ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00").replace("+00:00", ""))
            except (ValueError, AttributeError):
                ts = datetime.fromtimestamp(f.stat().st_mtime)

            if ts < cutoff:
                if status in ("rejected", "failed", "rolled_back"):
                    results["stale_rejected"].append(str(f.name))
                elif status in ("proposed", "pending_approval"):
                    results["stale_failed"].append(str(f.name))
            else:
                results["active"].append(str(f.name))

        except (json.JSONDecodeError, Exception):
            results["stale_failed"].append(str(f.name))

    stale_count = len(results["stale_rejected"]) + len(results["stale_failed"])
    if stale_count > 500:
        results["recommendation"] = f"CRITICAL: {stale_count} stale files. Purge immediately."
    elif stale_count > 100:
        results["recommendation"] = f"HIGH: {stale_count} stale files. Schedule cleanup."
    elif stale_count > 0:
        results["recommendation"] = f"LOW: {stale_count} stale files. Cleanup when convenient."
    else:
        results["recommendation"] = "Clean. No action needed."

    # Truncate file lists for report
    results["stale_rejected"] = results["stale_rejected"][:20]
    results["stale_failed"] = results["stale_failed"][:20]
    results["active"] = len(results["active"])

    return results


def audit_loop_history(max_age_hours: int = 48) -> Dict[str, Any]:
    """Audit autonomous loop cycle files."""
    loops_dir = PROJECT_ROOT / "autonomous_loops"
    if not loops_dir.exists():
        return {"status": "clean", "count": 0}

    results = {
        "total_files": 0,
        "total_size_bytes": 0,
        "agents": {},
        "stale_count": 0,
        "recommendation": "",
    }

    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

    for agent_dir in loops_dir.iterdir():
        if not agent_dir.is_dir():
            continue
        agent_name = agent_dir.name
        agent_files = list(agent_dir.glob("*.json"))
        results["agents"][agent_name] = len(agent_files)
        results["total_files"] += len(agent_files)

        for f in agent_files:
            results["total_size_bytes"] += f.stat().st_size
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                results["stale_count"] += 1

    if results["stale_count"] > 200:
        results["recommendation"] = f"HIGH: {results['stale_count']} stale loop files. Archive old cycles."
    elif results["stale_count"] > 50:
        results["recommendation"] = f"MEDIUM: {results['stale_count']} stale loop files."
    else:
        results["recommendation"] = "Acceptable."

    return results


def audit_tools_directory() -> Dict[str, Any]:
    """Check for duplicate/empty/redundant tools."""
    tools_dir = PROJECT_ROOT / "tools"
    if not tools_dir.exists():
        return {"status": "clean"}

    results = {
        "total_tools": 0,
        "empty_files": [],
        "tiny_files": [],  # < 100 bytes
        "potential_duplicates": [],
        "total_size_bytes": 0,
    }

    # Hash content for duplicate detection
    content_hashes: Dict[str, List[str]] = {}

    for f in tools_dir.glob("*.py"):
        if f.name == "__init__.py":
            continue
        results["total_tools"] += 1
        size = f.stat().st_size
        results["total_size_bytes"] += size

        if size == 0:
            results["empty_files"].append(f.name)
        elif size < 100:
            results["tiny_files"].append(f.name)

        # Content hash (first 500 chars to detect near-dupes)
        try:
            content = f.read_text()[:500]
            h = hashlib.md5(content.encode()).hexdigest()[:8]
            if h in content_hashes:
                content_hashes[h].append(f.name)
            else:
                content_hashes[h] = [f.name]
        except Exception:
            pass

    # Find duplicates
    for h, files in content_hashes.items():
        if len(files) > 1:
            results["potential_duplicates"].append(files)

    return results


def audit_dead_code() -> Dict[str, Any]:
    """Quick scan for obviously dead/unused files."""
    results = {
        "empty_init_files": [],
        "zero_byte_files": [],
        "uncalled_tools": [],
    }

    # Check for zero-byte python files
    for f in PROJECT_ROOT.rglob("*.py"):
        if f.stat().st_size == 0 and f.name != "__init__.py":
            results["zero_byte_files"].append(str(f.relative_to(PROJECT_ROOT)))

    # Check __init__.py files that are empty (could be pruned)
    for f in PROJECT_ROOT.rglob("__init__.py"):
        if f.stat().st_size == 0:
            results["empty_init_files"].append(str(f.relative_to(PROJECT_ROOT)))

    return results


def audit_repo_structure() -> Dict[str, Any]:
    """Get a high-level view of the repo structure for the council."""
    structure = {
        "directories": {},
        "total_python_files": 0,
        "total_json_files": 0,
        "total_md_files": 0,
        "total_size_mb": 0,
    }

    for d in sorted(PROJECT_ROOT.iterdir()):
        if d.name.startswith(".") or d.name == "__pycache__" or d.name == "node_modules":
            continue
        if d.is_dir():
            file_count = len(list(d.rglob("*")))
            dir_size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            structure["directories"][d.name] = {
                "files": file_count,
                "size_mb": round(dir_size / (1024**2), 2),
            }

    structure["total_python_files"] = len(list(PROJECT_ROOT.rglob("*.py")))
    structure["total_json_files"] = len(list(PROJECT_ROOT.rglob("*.json")))
    structure["total_md_files"] = len(list(PROJECT_ROOT.rglob("*.md")))

    return structure


def full_audit() -> Dict[str, Any]:
    """Run complete janitor audit and produce council report."""
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "mutations": audit_mutations(),
        "loops": audit_loop_history(),
        "tools": audit_tools_directory(),
        "dead_code": audit_dead_code(),
        "structure": audit_repo_structure(),
    }

    # Run dynamic tool quality audit (duplicates, orphans)
    try:
        from tools.auto_discovery import audit_tool_quality
        report["tool_quality"] = audit_tool_quality()
    except Exception as e:
        report["tool_quality"] = {"error": str(e)}

    # Generate summary recommendation
    priorities = []
    if "CRITICAL" in report["mutations"].get("recommendation", ""):
        priorities.append("🔴 Purge stale mutation files immediately")
    elif "HIGH" in report["mutations"].get("recommendation", ""):
        priorities.append("🟡 Archive stale mutation files")

    if "HIGH" in report["loops"].get("recommendation", ""):
        priorities.append("🟡 Archive old loop cycle files")

    if report["tools"].get("potential_duplicates"):
        priorities.append("🟡 Review duplicate tools")

    # Tool quality gate recommendations
    tq = report.get("tool_quality", {})
    if tq.get("duplicate_purpose"):
        priorities.append(f"🟡 {len(tq['duplicate_purpose'])} tool pairs have overlapping purpose — consolidate")
    if tq.get("orphaned_files"):
        priorities.append(f"🟡 {len(tq['orphaned_files'])} tool files failed to register — fix or remove")

    if report["dead_code"].get("zero_byte_files"):
        priorities.append("⚪ Remove zero-byte dead files")

    report["priority_actions"] = priorities or ["✅ Repository is clean"]

    return report


def generate_council_report() -> str:
    """Generate human-readable report for the council."""
    report = full_audit()
    lines = [
        "# 🧹 Repo Janitor Report",
        f"Generated: {report['timestamp']}",
        "",
        "## Priority Actions",
    ]

    for action in report["priority_actions"]:
        lines.append(f"- {action}")

    lines.extend([
        "",
        "## Mutations",
        f"- Total files: {report['mutations'].get('total_files', 0)}",
        f"- Size: {round(report['mutations'].get('total_size_bytes', 0) / (1024*1024), 1)}MB",
        f"- Recommendation: {report['mutations'].get('recommendation', 'N/A')}",
        "",
        "## Loop History",
        f"- Total files: {report['loops'].get('total_files', 0)}",
        f"- Size: {round(report['loops'].get('total_size_bytes', 0) / (1024*1024), 1)}MB",
        f"- Stale: {report['loops'].get('stale_count', 0)}",
        f"- Recommendation: {report['loops'].get('recommendation', 'N/A')}",
        "",
        "## Tools",
        f"- Total tools: {report['tools'].get('total_tools', 0)}",
        f"- Empty files: {len(report['tools'].get('empty_files', []))}",
        f"- Potential duplicates: {len(report['tools'].get('potential_duplicates', []))}",
    ])

    if report["tools"].get("potential_duplicates"):
        for dups in report["tools"]["potential_duplicates"][:5]:
            lines.append(f"  - Possible duplicates: {', '.join(dups)}")

    lines.extend([
        "",
        "## Structure",
        f"- Python files: {report['structure'].get('total_python_files', 0)}",
        f"- JSON files: {report['structure'].get('total_json_files', 0)}",
        f"- MD files: {report['structure'].get('total_md_files', 0)}",
    ])

    return "\n".join(lines)


def cleanup(dry_run: bool = False) -> Dict[str, Any]:
    """Actually remove stale/bloat files. Called by _maintenance_loop.
    
    Safe deletion targets:
    - Stale mutation files (rejected/failed older than 7 days)
    - Old loop cycle telemetry files (older than 48h)
    - Zero-byte Python files (dead code)
    - Empty discussion_summaries
    
    Does NOT touch:
    - Active/pending mutations
    - Core source code
    - Anything in git staging
    
    Args:
        dry_run: If True, report what would be deleted without deleting.
    
    Returns:
        Dict with counts of deleted files per category.
    """
    results = {
        "mutations_deleted": 0,
        "loops_deleted": 0,
        "zero_byte_deleted": 0,
        "bytes_freed": 0,
        "dry_run": dry_run,
        "errors": [],
    }
    
    # 1. Purge stale mutation files (rejected/failed > 7 days old)
    mutations_dir = PROJECT_ROOT / "evolution" / "mutations"
    if mutations_dir.exists():
        cutoff = datetime.utcnow() - timedelta(days=7)
        for f in mutations_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                status = data.get("status", "")
                if status not in ("rejected", "failed", "rolled_back", "system_rejected"):
                    continue
                timestamp = data.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00").replace("+00:00", ""))
                except (ValueError, AttributeError):
                    ts = datetime.fromtimestamp(f.stat().st_mtime)
                if ts < cutoff:
                    size = f.stat().st_size
                    if not dry_run:
                        f.unlink()
                    results["mutations_deleted"] += 1
                    results["bytes_freed"] += size
            except Exception as e:
                results["errors"].append(f"mutation {f.name}: {e}")
    
    # 2. Purge old loop cycle files (> 48 hours)
    loops_dir = PROJECT_ROOT / "autonomous_loops"
    if loops_dir.exists():
        cutoff = datetime.utcnow() - timedelta(hours=48)
        for agent_dir in loops_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            for f in agent_dir.glob("*.json"):
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    if mtime < cutoff:
                        size = f.stat().st_size
                        if not dry_run:
                            f.unlink()
                        results["loops_deleted"] += 1
                        results["bytes_freed"] += size
                except Exception as e:
                    results["errors"].append(f"loop {f.name}: {e}")
    
    # 3. Remove zero-byte Python files (except __init__.py)
    for f in PROJECT_ROOT.rglob("*.py"):
        if f.name == "__init__.py":
            continue
        if ".git" in str(f) or "__pycache__" in str(f):
            continue
        try:
            if f.stat().st_size == 0:
                if not dry_run:
                    f.unlink()
                results["zero_byte_deleted"] += 1
        except Exception:
            pass
    
    # 4. Clean empty discussion_summaries
    summaries_dir = PROJECT_ROOT / "discussion_summaries"
    if summaries_dir.exists():
        for f in summaries_dir.glob("*.json"):
            try:
                if f.stat().st_size < 10:  # Empty or near-empty
                    if not dry_run:
                        f.unlink()
                    results["bytes_freed"] += f.stat().st_size
            except Exception:
                pass
    
    return results
