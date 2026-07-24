# Operations Runbook

This runbook documents operational procedures for the Autonomous 3-Agent Council system, including key rotation, rollback recovery, and incident response.

## Table of Contents

1. [Key Rotation](#key-rotation)
2. [Rollback Recovery](#rollback-recovery)
3. [Incident Response](#incident-response)
4. [Model Management](#model-management)
5. [Audit Log Verification](#audit-log-verification)

---

## Key Rotation

### Overview

The system uses HMAC-SHA256 keys for:
- Audit log integrity (governance/audit_log.py)
- Snapshot integrity (core/snapshots.py)
- Zero-trust inter-agent communication (governance/zero_trust.py)

Keys are managed via `governance/keys.py` and stored in the `.keys/` directory.

### Rotating Keys

#### Automated Rotation (Recommended)

Use the key rotation CLI:

```powershell
# Rotate all keys
python -m governance.rotate_keys --all

# Rotate specific key
python -m governance.rotate_keys --key audit_log
python -m governance.rotate_keys --key snapshot
python -m governance.rotate_keys --key zero_trust

# Preview rotation (dry-run)
python -m governance.rotate_keys --all --dry-run
```

#### Manual Rotation

1. **Stop the council system**
   ```powershell
   # Ensure no processes are running
   Get-Process python | Where-Object {$_.Path -like "*autonomous*"} | Stop-Process
   ```

2. **Generate new key**
   ```powershell
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Update environment variable or .env file**
   ```powershell
   # Option A: Environment variable
   $env:AUDIT_LOG_HMAC_KEY="new_key_here"
   
   # Option B: Update .env file
   notepad .env
   # Update: AUDIT_LOG_HMAC_KEY=new_key_here
   ```

4. **Restart the system**
   ```powershell
   python main.py
   ```

5. **Verify new key is active**
   ```powershell
   # Check audit log uses new key
   python -c "from governance.audit_log import log_event; log_event('test', 'system', 'key_rotation', {})"
   ```

### Key Rotation Schedule

- **Production**: Rotate every 90 days
- **Development**: Rotate every 30 days
- **After incident**: Rotate immediately

### Key Rotation Checklist

- [ ] Notify team of scheduled rotation
- [ ] Backup current keys: `Copy-Item -Recurse .keys .keys_backup_$(Get-Date -Format 'yyyyMMdd')`
- [ ] Run rotation CLI or manual process
- [ ] Verify system starts successfully
- [ ] Test audit log integrity: `python -c "from governance.audit_log import verify_log_integrity; print(verify_log_integrity())"`
- [ ] Test snapshot integrity: `python -c "from core.snapshots import verify_snapshot_chain; print(verify_snapshot_chain('test_node'))"`
- [ ] Document rotation in session_log.md

---

## Rollback Recovery

### Overview

The system implements SAGA pattern rollbacks for multi-step failures. Rollback states are stored in the `rollback_states/` directory.

### Identifying Failure

1. **Check audit logs**
   ```powershell
   # View recent errors
   Get-Content audit_logs\audit_$(Get-Date -Format 'yyyyMMdd').log | Select-String "error"
   
   # Verify log integrity
   python -c "from governance.audit_log import verify_log_integrity; verify_log_integrity()"
   ```

2. **Check snapshot chain**
   ```powershell
   python -c "from core.snapshots import verify_snapshot_chain; verify_snapshot_chain('autobot')"
   ```

3. **Review reasoning snapshots**
   ```powershell
   Get-ChildItem reasoning_snapshots\*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 10
   ```

### Manual Rollback Procedure

1. **Identify last stable state**
   ```powershell
   # List available checkpoints
   Get-ChildItem rollback_states\checkpoint_*.json | Sort-Object LastWriteTime -Descending
   ```

2. **Review checkpoint contents**
   ```powershell
   # View latest checkpoint
   Get-Content rollback_states\checkpoint_*.json | Select-Object -Last 1 | ConvertFrom-Json | Format-List
   ```

3. **Restore from checkpoint**
   ```powershell
   python -c "from core.rollback import rollback_to_checkpoint; rollback_to_checkpoint('checkpoint_id_here')"
   ```

4. **Verify restoration**
   ```powershell
   # Check state consistency
   python -c "from core.state import AgentState; print('State restored successfully')"
   ```

### Automated Rollback

The system automatically triggers rollback when:
- Loop count exceeds TTL (5 iterations)
- Node execution fails with exception
- Semantic loop detected (same action repeated 3 times)

To enable automatic rollback:
```python
# In core/graph.py, ensure error_handler is configured
workflow.add_node("error_handler", error_handler_node)
```

### Rollback Recovery Checklist

- [ ] Identify failure point from audit logs
- [ ] Verify audit log integrity
- [ ] Locate last stable checkpoint
- [ ] Review checkpoint state
- [ ] Execute rollback
- [ ] Verify system state consistency
- [ ] Test council operation with simple task
- [ ] Document incident in session_log.md

---

## Incident Response

### Security Incident

**Scenario**: Suspected unauthorized code execution or data exfiltration

1. **Immediate Actions**
   ```powershell
   # Stop all council processes
   Get-Process python | Stop-Process -Force
   
   # Isolate network (if needed)
   # Disable network adapter or firewall rule
   ```

2. **Preserve Evidence**
   ```powershell
   # Backup audit logs
   Copy-Item -Recurse audit_logs "audit_logs_incident_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
   
   # Backup snapshots
   Copy-Item -Recurse reasoning_snapshots "snapshots_incident_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
   
   # Backup rollback states
   Copy-Item -Recurse rollback_states "rollback_incident_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
   ```

3. **Rotate All Keys**
   ```powershell
   python -m governance.rotate_keys --all
   ```

4. **Review Audit Trail**
   ```powershell
   # Search for suspicious activity
   Get-Content audit_logs\*.log | Select-String "shell_exec|load_tool|execute_tool"
   ```

5. **Verify System Integrity**
   ```powershell
   # Check for unauthorized tool registrations
   python -c "from tools.mcp_registry import get_registered_tools; print(get_registered_tools())"
   
   # Verify sandbox isolation
   python -c "from core.sandbox import execute_in_sandbox; print(execute_in_sandbox('echo test'))"
   ```

### Performance Incident

**Scenario**: System running slowly or consuming excessive resources

1. **Check Resource Usage**
   ```powershell
   # Monitor RAM usage
   Get-Process python | Select-Object Id, CPU, WorkingSet64
   
   # Check Ollama models loaded
   ollama ps
   ```

2. **Verify Sequential Loading**
   ```powershell
   # Ensure only 1 model loaded at a time
   $env:OLLAMA_MAX_LOADED_MODELS="1"
   ```

3. **Run Preflight Check**
   ```powershell
   python -m core.model_check
   ```

4. **Clear Caches**
   ```powershell
   # Clear semantic cache
   python -c "from core.semantic_cache import clear_cache; clear_cache()"
   ```

### Data Corruption Incident

**Scenario**: Audit log or snapshot integrity check fails

1. **Identify Corruption Point**
   ```powershell
   # Check audit log integrity
   python -c "from governance.audit_log import verify_log_integrity; result = verify_log_integrity(); print(result)"
   
   # Check snapshot chain
   python -c "from core.snapshots import verify_snapshot_chain; result = verify_snapshot_chain('node_name'); print(result)"
   ```

2. **Restore from Backup**
   ```powershell
   # If backup exists
   Copy-Item -Recurse audit_logs_backup audit_logs -Force
   ```

3. **Reinitialize if Necessary**
   ```powershell
   # Backup corrupted data
   Move-Item audit_logs audit_logs_corrupted_$(Get-Date -Format 'yyyyMMdd_HHmmss')
   
   # Create fresh log directory
   New-Item -ItemType Directory audit_logs
   ```

---

## Model Management

### Checking Model Availability

```powershell
# Run preflight check
python -m core.model_check

# List installed models
ollama list

# Check model details
ollama show qwen2.5:3b
```

### Installing Models

```powershell
# Install required models
ollama pull qwen2.5:3b
ollama pull phi3:mini
ollama pull deepseek-coder:1.3b

# Install fallback model
ollama pull llama3.2:1b
```

### Updating Models

```powershell
# Pull latest version
ollama pull qwen2.5:3b

# Remove old version
ollama rm qwen2.5:3b-old
```

### Model Fallback Configuration

Edit `.env` to configure fallback models:
```env
AUTOBOT_MODEL=qwen2.5:3b
AUTOBOT_FALLBACK_MODEL=llama3.2:1b
ALPHA_MODEL=phi3:mini
ALPHA_FALLBACK_MODEL=llama3.2:1b
BETA_MODEL=deepseek-coder:1.3b
BETA_FALLBACK_MODEL=llama3.2:1b
```

---

## Audit Log Verification

### Verifying Log Integrity

```powershell
# Verify today's log
python -c "from governance.audit_log import verify_log_integrity; result = verify_log_integrity(); print('Valid' if result['valid'] else 'Invalid')"

# Verify specific date
python -c "from governance.audit_log import verify_log_integrity; result = verify_log_integrity('20260725'); print(result)"
```

### Viewing Audit Logs

```powershell
# View recent entries
Get-Content audit_logs\audit_$(Get-Date -Format 'yyyyMMdd').log | Select-Object -Last 20

# Search for specific events
Get-Content audit_logs\*.log | Select-String "tool_invocation"

# Export to CSV
Import-Csv audit_logs\audit_*.log | Export-Csv audit_export.csv
```

### Log Rotation

Audit logs are automatically rotated daily. To manually rotate:

```powershell
# Archive old logs
$archiveDate = (Get-Date).AddDays(-30).ToString('yyyyMMdd')
Move-Item "audit_logs\audit_$archiveDate.log" "audit_logs\archive\"
```

---

## Emergency Contacts

- **System Administrator**: [Contact Info]
- **Security Team**: [Contact Info]
- **Development Lead**: [Contact Info]

---

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2026-07-25 | 1.0 | Initial runbook creation | Developer |

---

**Last Updated**: 2026-07-25
