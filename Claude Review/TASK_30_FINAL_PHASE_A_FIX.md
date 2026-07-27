# TASK 30: Add resource_impact to Mutation Serialization

**Status**: FINAL FIX - 5 minutes  
**Owner**: Kilo Code  
**Urgency**: Needed before Phase B  
**Commit to follow**: 339d787  

---

## THE ISSUE

Phase A Tasks 24-29 are working perfectly, but there's one small oversight:

**resource_impact is being set on mutations but not serialized to JSON**

When mutations are saved, the resource_impact field disappears.

---

## THE FIX (2 changes, 30 seconds)

### Change 1: Add to Mutation.__init__

**File**: `core/evolution.py`

**Find this line** (around line 122):
```python
self.quality_breakdown = None
```

**Add after it**:
```python
self.resource_impact = None
```

**Full context**:
```python
self.mission_pillar = None
self.mission_description = None
self.quality_score = None
self.quality_breakdown = None
self.resource_impact = None  # ← ADD THIS LINE
```

---

### Change 2: Add to Mutation.to_dict()

**File**: `core/evolution.py`

**Find this line** (around line 158):
```python
            "quality_breakdown": self.quality_breakdown
        }
```

**Add before the closing brace**:
```python
            "quality_breakdown": self.quality_breakdown,
            "resource_impact": self.resource_impact,
        }
```

**Full context**:
```python
def to_dict(self) -> Dict:
    return {
        "mutation_id": self.mutation_id,
        # ... other fields ...
        "quality_score": self.quality_score,
        "quality_breakdown": self.quality_breakdown,
        "resource_impact": self.resource_impact,  # ← ADD THIS LINE
    }
```

---

## VERIFICATION

After making changes:

```bash
# 1. Check Python syntax
python3 -m py_compile core/evolution.py

# 2. Verify lines were added
grep -n "resource_impact" core/evolution.py

# Expected output should show:
# - Line in __init__ (around 123)
# - Line in to_dict() (around 159)
```

---

## COMMIT & PUSH

```bash
# Check status
git status

# Add changes
git add core/evolution.py

# Commit
git commit -m "Task 30: Add resource_impact to Mutation serialization (to_dict)"

# Push
git push origin main
```

---

## VERIFICATION AFTER COMMIT

```bash
# Verify new mutations will have resource_impact
# (They won't generate until system runs again, but code will be ready)

# Check file syntax
python3 -m py_compile core/evolution.py && echo "✅ Compiles successfully"
```

---

## DONE

After this commit, Phase A is **100% complete** and ready for Phase B.

All mutations will now include:
- ✅ quality_score
- ✅ mission_pillar  
- ✅ quality_breakdown
- ✅ resource_impact

---

## NEXT: Phase B (Self-Deployment)

After this commit is verified, ready to start:
- Packaging components as microservices
- Deploying to free platforms (Hugging Face Spaces, Replit, etc)
- Building spider-web grid

---

## QUESTIONS?

None expected. This is straightforward.

Just 2 lines, 30 seconds, commit.

