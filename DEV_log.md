### Challenge: Module Import Error
**Problem:**
```
ModuleNotFoundError: No module named 'core'
```

**Root Cause:** 
When running Python files from subdirectories, Python doesn't automatically include parent directories in the module search path.

**Solution:**
Added path resolution at the top of files:
```python
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
```

**Files Modified:**
- `core/launcher.py`

**Time to Resolve:** 15 minutes