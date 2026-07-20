#!/usr/bin/env python3
import json, os, sys
f = '/opt/zinaida/sandbox/configs/autonomy_state.json'
try:
    if os.path.exists(f):
        with open(f, 'r') as fh:
            d = json.load(fh)
        d['errors_streak'] = 0
        with open(f, 'w') as fh:
            json.dump(d, fh, indent=2)
        print("✅ State reset: errors_streak = 0")
    else:
        print("⚠️ State file not found")
except Exception as e:
    print(f"⚠️ Reset warning: {e}", file=sys.stderr)
