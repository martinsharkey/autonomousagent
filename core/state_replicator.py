import json
import shutil
import hashlib
import os
import sqlite3
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class StateReplicator:
    """Multi-location state replication for durable local state."""

    def __init__(self, primary_path: str = ".", replicas: Optional[List[str]] = None):
        self.primary_path = Path(primary_path)
        self.replicas = [Path(p) for p in (replicas or [])]
        self.replica_meta_file = self.primary_path / "replica_meta.json"
        self._ensure_dirs()

    def _ensure_dirs(self):
        self.primary_path.mkdir(parents=True, exist_ok=True)
        for replica in self.replicas:
            replica.mkdir(parents=True, exist_ok=True)

    def _compute_db_hash(self, db_path: Path) -> Optional[str]:
        if not db_path.exists() or db_path.stat().st_size == 0:
            return None
        hasher = hashlib.sha256()
        with open(db_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()[:16]

    def _meta(self) -> Dict[str, Any]:
        if self.replica_meta_file.exists():
            try:
                return json.loads(self.replica_meta_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_meta(self, meta: Dict[str, Any]):
        self.replica_meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def register_replica(self, db_file: str, targets: Optional[List[str]] = None) -> Dict[str, Any]:
        target_paths = [Path(t) for t in (targets or [str(replica / db_file) for replica in self.replicas])]
        meta = self._meta()
        entry = meta.setdefault(db_file, {
            "registered_at": datetime.utcnow().isoformat(),
            "targets": []
        })
        existing = {t["path"] for t in entry.get("targets", [])}
        for target in target_paths:
            path_str = str(target)
            if path_str not in existing:
                entry["targets"].append({
                    "path": path_str,
                    "last_sync": None,
                    "last_hash": None,
                })
        self._save_meta(meta)
        return meta

    def replicate(self, db_file: str) -> Dict[str, Any]:
        source = self.primary_path / db_file
        if not source.exists():
            return {"status": "skipped", "reason": "source missing"}

        source_hash = self._compute_db_hash(source)
        meta = self._meta()
        entry = meta.setdefault(db_file, {"registered_at": datetime.utcnow().isoformat(), "targets": []})
        targets = entry.setdefault("targets", [])

        results = []
        for target_obj in targets:
            target_path = Path(target_obj.get("path", ""))
            if not target_path:
                continue
            try:
                if target_path.exists() and self._compute_db_hash(target_path) == source_hash:
                    results.append({"path": str(target_path), "status": "unchanged"})
                    continue

                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target_path)
                target_obj["last_sync"] = datetime.utcnow().isoformat()
                target_obj["last_hash"] = source_hash
                results.append({"path": str(target_path), "status": "synced"})
            except Exception as exc:
                results.append({"path": str(target_path), "status": "error", "error": str(exc)})

        self._save_meta(meta)
        return {"status": "ok", "source_hash": source_hash, "results": results}

    def replicate_all(self) -> Dict[str, Any]:
        report = {}
        for db_file, entry in self._meta().items():
            report[db_file] = self.replicate(db_file)
        return report

    def verify(self, db_file: str) -> Dict[str, Any]:
        source = self.primary_path / db_file
        source_hash = self._compute_db_hash(source)
        issues: List[str] = []
        details: List[Dict[str, Any]] = []

        for target_obj in self._meta().get(db_file, {}).get("targets", []):
            target_path = Path(target_obj.get("path", ""))
            detail = {"path": str(target_path), "exists": target_path.exists()}
            if not target_path.exists():
                detail["status"] = "missing"
                issues.append(f"missing replica: {target_path}")
            elif source_hash and self._compute_db_hash(target_path) != source_hash:
                detail["status"] = "mismatch"
                issues.append(f"hash mismatch: {target_path}")
            else:
                detail["status"] = "ok"
            details.append(detail)

        return {
            "db_file": db_file,
            "source_exists": source.exists(),
            "status": "healthy" if not issues else f"issues: {'; '.join(issues)}",
            "details": details,
        }

    def heal(self, db_file: str) -> Dict[str, Any]:
        source = self.primary_path / db_file
        if not source.exists():
            return {"status": "failed", "reason": "source missing, cannot heal"}

        source_hash = self._compute_db_hash(source)
        healed = []
        errors = []

        for target_obj in self._meta().get(db_file, {}).get("targets", []):
            target_path = Path(target_obj.get("path", ""))
            try:
                if not target_path.exists() or self._compute_db_hash(target_path) != source_hash:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target_path)
                    healed.append(str(target_path))
            except Exception as exc:
                errors.append({"path": str(target_path), "error": str(exc)})

        return {
            "db_file": db_file,
            "source_hash": source_hash,
            "healed": healed,
            "errors": errors,
            "status": "healed" if healed or not errors else "healthy",
        }
