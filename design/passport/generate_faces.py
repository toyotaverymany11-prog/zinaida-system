#!/usr/bin/env python3
"""Generate 5 face angles of Zinaida via Replicate API (black-forest-labs/flux-dev)."""

import requests
import time
import json
from datetime import datetime, timezone
import traceback

API_URL = "https://api.replicate.com/v1/predictions"
TOKEN = "r8_QZWTjkMnYM5LRtnRIz8xz9X3Q0zghkL3u5eXs"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

OUTPUT_DIR = "/opt/zinaida/design/passport"

base_prompt = "Professional portrait of young woman 28yo, dark hair, Slavic features, ultra-realistic skin with visible pores, natural texture, Shot on Canon EOS R5 85mm f1.4"

angles = [
    {
        "filename": "face_front_serious.png",
        "prompt": f"{base_prompt}, front view, serious expression, looking straight at camera, neutral face, Shot on Canon EOS R5 85mm f1.4"
    },
    {
        "filename": "face_front_smile.png",
        "prompt": f"{base_prompt}, front view, warm genuine smile, happy eyes, Shot on Canon EOS R5 85mm f1.4"
    },
    {
        "filename": "face_profile_left.png",
        "prompt": f"{base_prompt}, profile view facing left, side view, clean background, Shot on Canon EOS R5 85mm f1.4"
    },
    {
        "filename": "face_threequarter_left_serious.png",
        "prompt": f"{base_prompt}, three-quarter view facing left, serious expression, Shot on Canon EOS R5 85mm f1.4"
    },
    {
        "filename": "face_dramatic_lighting.png",
        "prompt": f"{base_prompt}, dramatic cinematic lighting, chiaroscuro, moody atmosphere, editorial style, Shot on Canon EOS R5 85mm f1.4"
    },
]

def run_prediction(prompt, max_retries=5):
    payload = {
        "version": "black-forest-labs/flux-dev",
        "input": {
            "prompt": prompt,
            "num_outputs": 1,
            "aspect_ratio": "3:4"
        }
    }
    for attempt in range(1, max_retries + 1):
        print(f"  POST {API_URL} (attempt {attempt}/{max_retries})")
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 429:
            body = resp.json()
            retry_after = body.get("retry_after", 3)
            print(f"  Rate limited! Retrying after {retry_after}s... Body: {resp.text[:300]}")
            time.sleep(retry_after + 2)
            continue
        if resp.status_code not in (200, 201):
            print(f"  Error response body: {resp.text[:1000]}")
            resp.raise_for_status()
        data = resp.json()
        pred_id = data.get("id")
        get_url = data.get("urls", {}).get("get")
        print(f"  Prediction ID: {pred_id}")
        print(f"  Get URL: {get_url}")
        return pred_id, get_url, data
    raise RuntimeError(f"Exhausted {max_retries} retries due to rate limiting")

def poll_prediction(get_url, timeout_sec=300):
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > timeout_sec:
            raise TimeoutError(f"Polling timed out after {timeout_sec}s")
        resp = requests.get(get_url, headers=HEADERS, timeout=30)
        data = resp.json()
        status = data.get("status")
        print(f"  Status: {status} (elapsed: {elapsed:.0f}s)")
        if status == "succeeded":
            return data
        elif status == "failed":
            error_msg = data.get("error", "Unknown error")
            logs = data.get("logs", "")
            raise RuntimeError(f"Prediction failed: {error_msg}\nLogs: {logs[:500]}")
        elif status == "canceled":
            raise RuntimeError("Prediction was canceled")
        time.sleep(5)

def download_image(url, filepath):
    print(f"  Downloading from {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        f.write(resp.content)
    file_size = len(resp.content)
    print(f"  Saved {filepath} ({file_size} bytes)")
    return file_size

results = []
for i, angle in enumerate(angles, 1):
    print(f"\n{'='*60}")
    print(f"[{i}/{len(angles)}] Generating: {angle['filename']}")
    print(f"{'='*60}")
    try:
        pred_id, get_url, initial_data = run_prediction(angle["prompt"])
        
        # If already completed in initial response
        if initial_data.get("status") == "succeeded":
            result_data = initial_data
        else:
            result_data = poll_prediction(get_url)
        
        output = result_data.get("output")
        if isinstance(output, list) and len(output) > 0:
            img_url = output[0]
        elif isinstance(output, str):
            img_url = output
        else:
            print(f"  Unexpected output format: {output}")
            raise ValueError(f"Cannot extract image URL from output: {output}")
        
        filepath = f"{OUTPUT_DIR}/{angle['filename']}"
        file_size = download_image(img_url, filepath)
        results.append({"filename": angle["filename"], "status": "success", "size": file_size})
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()
        results.append({"filename": angle["filename"], "status": "failed", "error": str(e)})

print(f"\n{'='*60}")
print("SUMMARY:")
for r in results:
    status_str = r['status']
    if r['status'] == 'success':
        status_str += f" ({r['size']} bytes)"
    print(f"  {r['filename']}: {status_str}")
print(f"{'='*60}")

# Print results as JSON for the orchestrator
print(f"\nFINAL_RESULTS_JSON:{json.dumps(results, indent=2)}")
