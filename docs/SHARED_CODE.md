# Shared Code Documentation

## md-viewer-common.js

This file is shared between diary-md and inventory-md projects.

### Source of Truth

**inventory-md** is the source of truth for `md-viewer-common.js`

Location: `src/inventory_md/templates/md-viewer-common.js`

### Automatic Sync

A git post-commit hook in inventory-md automatically copies the file to diary-md when modified.

**How it works:**
1. You modify `md-viewer-common.js` in inventory-md
2. You commit in inventory-md
3. Hook automatically copies to `diary-md/viewer/md-viewer-common.js`
4. File is staged in diary-md (you need to commit manually)

### Making Changes

**✅ Correct way:**
```bash
cd /home/tobias/inventory-system
# Edit src/inventory_md/templates/md-viewer-common.js
git add src/inventory_md/templates/md-viewer-common.js
git commit -m "Update shared viewer library"
# File automatically copied to diary-md

cd /home/tobias/diary-md
git status  # File is staged
git commit -m "Sync md-viewer-common.js from inventory-md"
```

**⚠️ Warning:**
If you try to modify `viewer/md-viewer-common.js` in diary-md directly, you'll get a warning:
```
⚠️  WARNING: You are modifying viewer/md-viewer-common.js
⚠️  This file is synced from inventory-md
```

To bypass the warning (for urgent fixes):
```bash
git commit --no-verify
# Then remember to sync back to inventory-md manually!
```

### Manual Sync (if needed)

If automatic sync fails or you need to sync manually:

```bash
# Copy from inventory-md to diary-md
cp /home/tobias/inventory-system/src/inventory_md/templates/md-viewer-common.js \
   /home/tobias/diary-md/viewer/md-viewer-common.js
```

### Git Hooks Location

**inventory-md:**
- `.git/hooks/post-commit` - Copies file after commit

**diary-md:**
- `.git/hooks/pre-commit` - Warns if file is modified

### Last Synced

Check the git log:
```bash
cd /home/tobias/diary-md
git log --oneline viewer/md-viewer-common.js | head -1
```

### Troubleshooting

**Sync didn't happen:**
1. Check hook is executable: `ls -l .git/hooks/post-commit`
2. Check paths in hook are correct
3. Check file was actually modified in commit

**Conflicts:**
1. Always accept inventory-md version
2. Manually port any diary-md specific changes back to inventory-md
3. Re-commit in inventory-md to sync

---

**Last updated:** 2026-01-23
