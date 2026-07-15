#!/usr/bin/env python3
"""
Group Chat Agent Recovery Script
Переподключает агентов в групповой чат после рестарта Hermes Web UI.
Запускается как systemd oneshot после hermes-web-ui.service
"""

import json
import urllib.request
import hmac
import hashlib
import base64
import time
import sys
import os

WEB_UI_URL = "http://127.0.0.1:8648"
ROOM_ID = "mrj9nkx8nln7lx"
AGENTS = [
    {"profile": "olya", "name": "Оля (архитектор)", "description": ""},
    {"profile": "default", "name": "Default (контент-завод)", "description": ""},
]

def get_jwt():
    """Generate JWT from the Web UI token file"""
    # Try multiple locations for the token
    token_paths = [
        "/root/.hermes-web-ui/.token",
        "/root/.hermes/.token",
        os.path.expanduser("~/.hermes-web-ui/.token"),
        os.path.expanduser("~/.hermes/.token"),
    ]
    
    secret = None
    for p in token_paths:
        try:
            with open(p, 'r') as f:
                secret = f.read().strip()
                if secret:
                    break
        except (FileNotFoundError, PermissionError):
            continue
    
    if not secret:
        # Try AUTH_TOKEN env var
        secret = os.environ.get("AUTH_TOKEN", "")
        if not secret:
            # Try HERMES_WEB_UI_TOKEN env var
            secret = os.environ.get("HERMES_WEB_UI_TOKEN", "")
    
    if not secret:
        print("ERROR: Cannot find auth token")
        sys.exit(1)
    
    # Build JWT
    header_b64 = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b'=').decode()
    
    payload = {
        "sub": "1",
        "username": "ZinaidaSecure2026",
        "role": "super_admin",
        "type": "access",
        "aud": "hermes-web-ui",
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,  # 1 minute JWT
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b'=').decode()
    
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()
    
    return f"{signing_input}.{sig_b64}"


def api_call(method, path, body=None):
    """Make an authenticated API call to Hermes Web UI"""
    jwt = get_jwt()
    url = f"{WEB_UI_URL}{path}"
    data = json.dumps(body).encode() if body else None
    
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {jwt}")
    req.add_header("Content-Type", "application/json")
    
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_text = e.read().decode()
        print(f"HTTP {e.code} on {method} {path}: {error_text[:200]}")
        return None
    except Exception as e:
        print(f"Error on {method} {path}: {e}")
        return None


def repair_agents():
    """Check and re-add agents to the room"""
    print(f"Checking room {ROOM_ID}...")
    
    # Get current room state
    room_data = api_call("GET", f"/api/hermes/group-chat/rooms/{ROOM_ID}")
    if not room_data:
        print("ERROR: Cannot get room data")
        return False
    
    room = room_data.get("room", {})
    current_agents = room_data.get("agents", [])
    
    print(f"Room: {room.get('name', 'unknown')}")
    print(f"Current agents: {len(current_agents)}")
    
    connected_profiles = {a["profile"] for a in current_agents}
    
    for agent in AGENTS:
        profile = agent["profile"]
        if profile in connected_profiles:
            # Agent exists - check if it needs reconnecting
            agent_data = next(a for a in current_agents if a["profile"] == profile)
            print(f"  Agent {profile} exists (invited={agent_data.get('invited', '?')}, "
                  f"id={agent_data.get('agentId', '?')[:12]}...)")
            
            # Try to DELETE and re-add to force fresh WebSocket connection
            agent_id = agent_data.get("agentId") or agent_data.get("id")
            if agent_id:
                print(f"  Removing {profile} ({agent_id[:12]}...) and re-adding...")
                del_result = api_call("DELETE", 
                    f"/api/hermes/group-chat/rooms/{ROOM_ID}/agents/{agent_id}")
                
                if del_result is None:
                    print(f"  WARNING: Failed to remove {profile}")
        else:
            print(f"  Agent {profile} NOT found in room")
        
        # Re-add agent
        print(f"  Adding {profile}...")
        add_result = api_call("POST", f"/api/hermes/group-chat/rooms/{ROOM_ID}/agents", {
            "profile": profile,
            "name": agent["name"],
            "description": agent["description"],
            "invited": True,
        })
        
        if add_result and add_result.get("agent"):
            a = add_result["agent"]
            print(f"  OK: {a['name']} (invited={a.get('invited', '?')})")
        else:
            print(f"  ERROR: Failed to add {profile}")
            return False
    
    return True


if __name__ == "__main__":
    # Wait for Web UI to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            resp = urllib.request.urlopen(f"{WEB_UI_URL}/health", timeout=2)
            if resp.status == 200:
                print(f"Web UI ready after {i+1}s")
                break
        except Exception:
            pass
        print(f"Waiting for Web UI... ({i+1}/{max_retries})")
        time.sleep(2)
    else:
        print("ERROR: Web UI did not become ready")
        sys.exit(1)
    
    success = repair_agents()
    if success:
        print("\nAgents repaired successfully!")
        sys.exit(0)
    else:
        print("\nFailed to repair agents")
        sys.exit(1)
