import hashlib
import tarfile
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from governance.decision_logger import DecisionLogger

class VersionStore:
    """Immutable code version repository"""
    
    def __init__(self, storage_dir: Path = Path("./versions")):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(exist_ok=True)
        self.manifest_file = self.storage_dir / "manifest.json"
        self.decision_logger = DecisionLogger()
        
        if not self.manifest_file.exists():
            self._write_manifest({})
    
    def _read_manifest(self) -> Dict:
        if self.manifest_file.exists():
            with open(self.manifest_file, "r") as f:
                return json.load(f)
        return {}
    
    def _write_manifest(self, manifest: Dict):
        with open(self.manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)
    
    def save_version(self, code: str, member_id: str, 
                     mutation_id: str, parent_version: str = None) -> str:
        """Save code version immutably. Returns version_id."""
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:12]
        version_id = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}_{code_hash}"
        
        version_file = self.storage_dir / f"{version_id}.tar.gz"
        
        if version_file.exists():
            raise ValueError(f"Version {version_id} already exists (immutable)")
        
        with tarfile.open(version_file, "w:gz") as tar:
            code_bytes = code.encode('utf-8')
            import io
            code_file = io.BytesIO(code_bytes)
            tarinfo = tarfile.TarInfo(name="code")
            tarinfo.size = len(code_bytes)
            tar.addfile(tarinfo, code_file)
        
        manifest = self._read_manifest()
        manifest[version_id] = {
            "timestamp": datetime.now().isoformat(),
            "member_id": member_id,
            "mutation_id": mutation_id,
            "parent_version": parent_version,
            "code_hash": code_hash,
            "storage_path": str(version_file),
            "rollback_safe": True
        }
        self._write_manifest(manifest)
        
        self.decision_logger.log(
            decision_type="VERSION_SAVED",
            metadata={
                "version_id": version_id,
                "code_hash": code_hash,
                "parent_version": parent_version
            },
            mutation_id=mutation_id,
            council_member=member_id
        )
        
        return version_id
    
    def get_version(self, version_id: str) -> str:
        """Retrieve code from version (immutable read)"""
        manifest = self._read_manifest()
        if version_id not in manifest:
            raise FileNotFoundError(f"Version {version_id} not found")
        
        version_file = self.storage_dir / f"{version_id}.tar.gz"
        extract_dir = self.storage_dir / version_id
        extract_dir.mkdir(exist_ok=True)
        
        with tarfile.open(version_file, "r:gz") as tar:
            tar.extractall(path=extract_dir)
        
        code_path = extract_dir / "code"
        with open(code_path, "r") as f:
            return f.read()
    
    def get_history(self, member_id: str = None) -> List[Dict]:
        """Get version lineage (parent → child chain)"""
        manifest = self._read_manifest()
        if member_id:
            return [v for v in manifest.values() if v["member_id"] == member_id]
        return list(manifest.values())
    
    def get_version_lineage(self, version_id: str) -> List[str]:
        """Get full lineage from version_id back to root"""
        manifest = self._read_manifest()
        lineage = []
        current = version_id
        
        while current and current in manifest:
            lineage.append(current)
            current = manifest[current].get("parent_version")
        
        return lineage
    
    def verify_integrity(self, version_id: str) -> bool:
        """Verify version integrity by checking hash"""
        manifest = self._read_manifest()
        if version_id not in manifest:
            return False
        
        expected_hash = manifest[version_id]["code_hash"]
        code = self.get_version(version_id)
        actual_hash = hashlib.sha256(code.encode()).hexdigest()[:12]
        
        return expected_hash == actual_hash
