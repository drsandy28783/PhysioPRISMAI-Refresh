# 🚨 EMERGENCY ROLLBACK GUIDE
**PhysioPRISM Code Cleanup - Instant Recovery Procedures**

---

## ⚡ INSTANT ROLLBACK (30 seconds)

If **ANYTHING** breaks after cleanup, use this command:

```bash
# Navigate to Recovery folder
cd "D:\New folder\New folder\Recovery"

# Rollback to pre-cleanup state
git reset --hard v1.0-before-cleanup

# Verify rollback
git status
# Should show: "HEAD detached at v1.0-before-cleanup"
```

**Done! Your app is back to working state.**

---

## 🔍 VERIFY ROLLBACK WORKED

```bash
# 1. Check files are restored
dir *.backup
# Should see all 9 .backup files

# 2. Check n8n file is restored
dir n8n_webhooks.py
# Should exist

# 3. Start app
python main.py
# Should start normally
```

---

## 🔧 PARTIAL ROLLBACK (Undo specific step)

If only ONE step caused issues, you can undo just that step:

### Find the problematic commit:
```bash
git log --oneline
# Output shows:
# abc1234 CLEANUP: Remove n8n_webhooks.py  <-- If this broke things
# def5678 CLEANUP: Remove diagnostic scripts
# ...
```

### Undo that specific commit:
```bash
# Option 1: Revert the commit (keeps history)
git revert abc1234

# Option 2: Go back before that commit
git reset --hard def5678  # Use the commit BEFORE the problem
```

---

## 💾 RESTORE FROM ZIP BACKUP

If git fails or you deleted the .git folder:

```bash
# 1. Delete current Recovery folder
cd "D:\New folder\New folder"
Remove-Item -Recurse -Force "Recovery"

# 2. Extract ZIP backup
# Find: Recovery-BACKUP-2026-01-30.zip (or similar)
# Right-click → Extract Here

# 3. Verify
cd Recovery
dir
# Should see all original files
```

---

## 📋 COMMON ROLLBACK SCENARIOS

### Scenario 1: "ModuleNotFoundError: No module named 'n8n_webhooks'"

**Cause:** Something is still importing n8n_webhooks.py

**Fix:**
```bash
# Rollback Step 1.5 only
git revert HEAD  # If Step 1.5 was last commit

# Then investigate
grep -r "n8n_webhooks" *.py
# This will show which file is importing it
# Report findings to AI assistant
```

---

### Scenario 2: "App won't start after cleanup"

**Cause:** Unknown

**Fix:**
```bash
# Full rollback
git reset --hard v1.0-before-cleanup

# Then cleanup ONE STEP AT A TIME
# Test after each step to find the problematic one
```

---

### Scenario 3: "Git commands not working"

**Cause:** Git not initialized or .git folder deleted

**Fix:**
```bash
# Use ZIP backup instead
cd "D:\New folder\New folder"
Remove-Item -Recurse -Force "Recovery"

# Extract: Recovery-BACKUP-2026-01-30.zip
# Extraction gives you the working version
```

---

## ✅ POST-ROLLBACK CHECKLIST

After rollback, verify:

- [ ] App starts: `python main.py`
- [ ] No import errors in console
- [ ] Web interface accessible: http://localhost:5000
- [ ] Login page loads
- [ ] Can log in successfully

If all ✅ checked, rollback successful!

---

## 📞 SUPPORT AFTER ROLLBACK

**After successful rollback:**

1. **Do not retry cleanup without investigation**
2. **Identify which step caused the issue**
3. **Provide to AI assistant:**
   - Error message (screenshot)
   - Which step failed (Step 1.1, 1.2, etc.)
   - Output of: `git log --oneline`
4. **AI assistant will create a revised cleanup plan**

---

## 🛡️ PREVENTION

**Before starting cleanup again:**

1. Test each step individually
2. Don't rush - one step per day is fine
3. Always verify app works after each step
4. Create new git commit after each successful step

---

## 📝 ROLLBACK HISTORY LOG

**Use this to track if you had to rollback:**

| Date | Step Failed | Reason | Resolution |
|------|------------|--------|------------|
| ___ | ___ | ___ | ___ |

---

**Remember:** Rollback is NOT a failure. It's a safety feature. Better to rollback and investigate than to have a broken app!
