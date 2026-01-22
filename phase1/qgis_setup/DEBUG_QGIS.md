# Debugging QGIS SIP Error

## Current Status

✅ **Startup script exists**: `~/.local/share/QGIS/QGIS3/profiles/default/python/startup.py`
✅ **Script logic works**: Tested and confirmed
✅ **QGIS bindings available**: `/usr/lib/python3/dist-packages/qgis` exists

## The Problem

QGIS GUI's Python console shows:
```
Couldn't load SIP module.
ModuleNotFoundError: No module named 'qgis'
```

This happens because QGIS's Python path doesn't include `/usr/lib/python3/dist-packages`.

## The Solution

We've created a startup script that QGIS should load automatically. However, if it's still not working:

### Step 1: Verify Startup Script

```bash
# Check if script exists
ls -la ~/.local/share/QGIS/QGIS3/profiles/default/python/startup.py

# View the script
cat ~/.local/share/QGIS/QGIS3/profiles/default/python/startup.py
```

### Step 2: Test the Script Manually

```bash
cd phase1
source ../.venv/bin/activate
python test_qgis_startup.py
```

This will verify the logic works.

### Step 3: Update to Enhanced Version

```bash
cd phase1
source ../.venv/bin/activate
python fix_qgis_python_v2.py
```

This creates a version with debug output.

### Step 4: Restart QGIS and Check Console

1. **Close QGIS completely** (not just the window - check for running processes)
2. **Restart QGIS**
3. **Open Python Console**: Plugins → Python Console
4. **Look for debug output** - you should see:
   ```
   ============================================================
   QGIS Startup Script Running...
   ✓ Added /usr/lib/python3/dist-packages to sys.path
   ✓ PyQt5.sip imported successfully
   ✓ qgis.core imported successfully!
   ```

### Step 5: If Still Not Working

#### Option A: Check QGIS Logs

QGIS logs are usually in:
- `~/.local/share/QGIS/QGIS3/profiles/default/logs/`
- Or check system logs: `journalctl -u qgis` (if running as service)

#### Option B: Check if Startup Script is Being Loaded

The enhanced version prints debug output. If you don't see it, the script isn't being loaded.

Possible reasons:
1. **Wrong profile**: QGIS might be using a different profile
   ```bash
   ls -la ~/.local/share/QGIS/QGIS3/profiles/
   ```
   Check which profile is active in QGIS: Settings → User Profiles

2. **Startup script disabled**: Check QGIS settings
   - Settings → Options → Python
   - Make sure "Enable Python console" is checked

3. **Script syntax error**: Test the script manually
   ```bash
   python3 ~/.local/share/QGIS/QGIS3/profiles/default/python/startup.py
   ```

#### Option C: Create Startup Script in All Profiles

```bash
# Find all profiles
find ~/.local/share/QGIS/QGIS3/profiles -type d -name "python" | while read dir; do
    cp ~/.local/share/QGIS/QGIS3/profiles/default/python/startup.py "$dir/startup.py"
    echo "Copied to $dir"
done
```

#### Option D: Manual Fix in QGIS Console

If the startup script isn't working, you can manually fix it each time:

1. Open QGIS Python Console
2. Run:
   ```python
   import sys
   sys.path.insert(0, '/usr/lib/python3/dist-packages')
   import qgis.core
   ```

3. Save this as a macro or plugin for convenience

## Verification

After applying the fix, verify it works:

1. Open QGIS Python Console
2. Run:
   ```python
   import qgis.core
   print(qgis.core.Qgis.QGIS_VERSION)
   ```
3. Should work without errors!

## Alternative: Use qgis_process Instead

If the GUI Python console continues to have issues, remember:
- **QGIS GUI works fine** for drawing boundaries
- **Our Phase 1 scripts work fine** (they use their own Python environment)
- **qgis_process CLI works fine** for headless operations

The SIP error only affects QGIS's built-in Python console, which we don't strictly need for the workflow.
