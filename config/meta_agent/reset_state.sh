#!/bin/bash
python3 << 'PYEOF'
import json, os
f = '/opt/zinaida/sandbox/configs/autonomy_state.json'
try:
    if os.path.exists(f):
        d = json.load(open(f))
        d['errors_streak'] = 0
        json.dump(d, open(f, 'w'), indent=2)
PYEOF
