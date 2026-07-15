#!/usr/bin/env python3
"""
Test face generation with IP-Adapter Face ID via Replicate API.
Generates 2 test photos preserving Zinaida's facial identity.
"""
import os
import sys
import time
import json
import traceback

# --- Config ---
# Token: prefer env var, fallback to file
TOKEN = os.environ.get("REPLICATE_API_TOKEN")
if not TOKEN:
    # Try to read from generate_faces.py (search for TOKEN = "r8_...")
    try:
        with open("/opt/zinaida/design/passport/generate_faces.py") as f:
            for line in f:
                if line.strip().startswith("TOKEN ="):
                    parts = line.split("=", 1)
                    val = parts[1].strip().strip('"').strip("'")
                    if val and val != "r8_QZW...5eXs":
                        TOKEN = val
                        break
    except Exception:
        pass

if not TOKEN:
    print("ERROR: No REPLICATE_API_TOKEN found in env or generate_faces.py")
    sys.exit(1)

OUTPUT_DIR = "/opt/zinaida/design/passport/generated"
REFERENCE_DIR = "/opt/zinaida/design/passport/originals"
REFERENCE_PHOTO = os.path.join(REFERENCE_DIR, "photo1.png")

# Check reference exists
if not os.path.exists(REFERENCE_PHOTO):
    # Try others
    for alt in ["photo2.png", "photo3.jpg"]:
        p = os.path.join(REFERENCE_DIR, alt)
        if os.path.exists(p):
            REFERENCE_PHOTO = p
            break

if not os.path.exists(REFERENCE_PHOTO):
    print(f"ERROR: No reference photo found in {REFERENCE_DIR}")
    sys.exit(1)

print(f"Using reference photo: {REFERENCE_PHOTO}")
print(f"Output dir: {OUTPUT_DIR}")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Prompts ---
prompt_front = (
    "passport photo of a woman, front view, neutral expression, "
    "looking straight at camera, ultra-realistic skin texture, natural pores, "
    "even lighting, plain gray background, Canon EOS R5 85mm f1.4, "
    "professional headshot, photorealistic, 8K, high detail"
)

prompt_45right = (
    "passport photo of a woman, 45 degree angle facing right, three-quarter view, "
    "neutral expression, ultra-realistic skin texture, natural pores, "
    "even lighting, plain gray background, Canon EOS R5 85mm f1.4, "
    "professional headshot, photorealistic, 8K, high detail"
)

negative_prompt = (
    "cartoon, anime, illustration, painting, drawing, CGI, 3D render, "
    "blurry, distorted face, asymmetrical, deformed eyes, bad anatomy, "
    "extra fingers, mutated hands, ugly, disfigured, low quality, "
    "worst quality, low resolution, watermark, text, logo, signature"
)

# --- Try multiple models in order ---
MODELS = [
    # IP-Adapter Face ID (most relevant)
    {
        "version": "fofr/ip-adapter-face-id",
        "provider": "fofr",
    },
    # IP-Adapter Face ID Plus
    {
        "version": "tencentarc/ip-adapter-face-id-plus",
        "provider": "tencentarc",
    },
    # Face to Sticker (can work as fallback)
    {
        "version": "fofr/face-to-sticker",
        "provider": "fofr",
    },
]

# --- Helper functions ---
def upload_to_replicate(filepath, timeout=120):
    """Upload a file to Replicate and return a URL."""
    import replicate
    print(f"  Uploading {filepath}...")
    try:
        url = replicate.files.create(open(filepath, "rb"))
        print(f"  Uploaded -> {url}")
        return url
    except Exception as e:
        print(f"  Upload failed: {e}")
        # Fallback: try direct file.open approach
        print("  Trying alternative upload...")
        try:
            import replicate
            client = replicate.Client(api_token=TOKEN)
            url = client.upload_file(filepath)
            print(f"  Uploaded (alt) -> {url}")
            return url
        except Exception as e2:
            print(f"  Alt upload also failed: {e2}")
            return None

def try_model(model_info, prompt, image_url, output_path):
    """Try generating with a specific model."""
    version = model_info["version"]
    print(f"\n  Attempting model: {version}")
    
    try:
        import replicate
        client = replicate.Client(api_token=TOKEN)
        
        # Replicate v1 SDK uses client.run() or client.predictions.create()
        # Check API
        input_data = {
            "image": image_url,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_outputs": 1,
            "num_inference_steps": 50,
            "guidance_scale": 3.0,
        }
        
        # fofr/face-to-sticker has different params
        if "face-to-sticker" in version:
            input_data = {
                "image": image_url,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": 50,
            }
        
        print(f"  Input data keys: {list(input_data.keys())}")
        
        # Try sync generation
        output = client.run(
            version,
            input=input_data
        )
        
        print(f"  Output type: {type(output)}")
        print(f"  Output: {str(output)[:200]}")
        
        # Extract URL from output
        if isinstance(output, list) and len(output) > 0:
            img_url = output[0]
        elif isinstance(output, str):
            img_url = output
        elif hasattr(output, 'url'):
            img_url = output.url
        else:
            print(f"  Unexpected output format: {output}")
            return False, None
        
        # Download
        print(f"  Downloading from: {img_url}")
        resp = __import__('requests').get(img_url, timeout=120)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        print(f"  Saved: {output_path} ({len(resp.content)} bytes)")
        return True, len(resp.content)
        
    except Exception as e:
        print(f"  Error with {version}: {e}")
        traceback.print_exc()
        return False, None

def try_via_requests(model_info, prompt, image_url, output_path):
    """Try via raw requests API."""
    version = model_info["version"]
    api_url = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
    
    input_data = {
        "image": image_url,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "num_outputs": 1,
        "num_inference_steps": 50,
        "guidance_scale": 3.0,
    }
    
    if "face-to-sticker" in version:
        input_data = {
            "image": image_url,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": 50,
        }
    
    payload = {
        "version": version,
        "input": input_data,
    }
    
    print(f"  POST {api_url} (requests path)...")
    
    for attempt in range(3):
        resp = __import__('requests').post(api_url, headers=headers, json=payload, timeout=120)
        print(f"  Status: {resp.status_code}")
        
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 5)
            print(f"  Rate limited. Retry after {retry_after}s")
            time.sleep(retry_after + 2)
            continue
        
        if resp.status_code not in (200, 201):
            print(f"  Response: {resp.text[:500]}")
            return False, None
        
        data = resp.json()
        get_url = data.get("urls", {}).get("get")
        if not get_url:
            print(f"  No get URL in response: {list(data.keys())}")
            return False, None
        
        # Poll
        print(f"  Prediction ID: {data.get('id')}, polling...")
        timeout_sec = 180
        start = time.time()
        while True:
            elapsed = time.time() - start
            if elapsed > timeout_sec:
                print("  Timeout!")
                return False, None
            
            poll_resp = __import__('requests').get(get_url, headers=headers, timeout=30)
            poll_data = poll_resp.json()
            status = poll_data.get("status")
            
            if status == "succeeded":
                output = poll_data.get("output")
                if isinstance(output, list) and len(output) > 0:
                    img_url = output[0]
                elif isinstance(output, str):
                    img_url = output
                else:
                    print(f"  Unexpected output: {output}")
                    return False, None
                
                print(f"  Downloading from {img_url}")
                dl_resp = __import__('requests').get(img_url, timeout=120)
                dl_resp.raise_for_status()
                with open(output_path, "wb") as f:
                    f.write(dl_resp.content)
                print(f"  Saved: {output_path} ({len(dl_resp.content)} bytes)")
                return True, len(dl_resp.content)
            
            elif status == "failed":
                print(f"  Failed: {poll_data.get('error', 'unknown')}")
                return False, None
            elif status == "canceled":
                print("  Canceled")
                return False, None
            
            time.sleep(5)
    
    return False, None


# --- Main execution ---
start_time = time.time()
results = {"model_used": None, "error": None, "success": False}

# Upload reference photo first
import replicate
print("Uploading reference photo to Replicate...")
try:
    # Try replicate.files.create
    ref_url = replicate.files.create(open(REFERENCE_PHOTO, "rb"))
    print(f"Reference uploaded: {ref_url}")
except Exception as e:
    print(f"Upload via files.create failed: {e}")
    try:
        # Try client.upload
        client = replicate.Client(api_token=TOKEN)
        ref_url = client.upload_file(REFERENCE_PHOTO)
        print(f"Reference uploaded (client): {ref_url}")
    except Exception as e2:
        print(f"Upload failed entirely: {e2}")
        ref_url = REFERENCE_PHOTO  # Use local path as last resort

# Define the two outputs
front_path = os.path.join(OUTPUT_DIR, "test_front.jpg")
right_path = os.path.join(OUTPUT_DIR, "test_45right.jpg")

# Try each model for each photo
for model_info in MODELS:
    version = model_info["version"]
    print(f"\n{'='*60}")
    print(f"Trying model: {version}")
    print(f"{'='*60}")
    
    # Try replicate SDK first, then raw requests
    success_front, size_front = try_model(model_info, prompt_front, ref_url, front_path)
    if not success_front:
        success_front, size_front = try_via_requests(model_info, prompt_front, ref_url, front_path)
    
    if not success_front:
        print(f"  SKIP: Front photo failed for {version}")
        continue
    
    # Try 45 degree
    success_right, size_right = try_model(model_info, prompt_45right, ref_url, right_path)
    if not success_right:
        success_right, size_right = try_via_requests(model_info, prompt_45right, ref_url, right_path)
    
    if not success_right:
        print(f"  SKIP: Right photo failed for {version}, but front succeeded")
        # Clean up front
        if os.path.exists(front_path):
            os.remove(front_path)
        continue
    
    # Both succeeded!
    results["model_used"] = version
    results["file_front"] = front_path
    results["file_45right"] = right_path
    results["front_size_bytes"] = size_front
    results["right_size_bytes"] = size_right
    results["success"] = True
    results["error"] = None
    break

# Fill in missing data
results["prompt_front"] = prompt_front
results["prompt_45right"] = prompt_45right
results["time_elapsed_seconds"] = round(time.time() - start_time, 1)

if not results["success"]:
    results["error"] = "All models failed for both angles"

# Print JSON
print(f"\n\nFINAL_RESULT_JSON:{json.dumps(results, indent=2, ensure_ascii=False)}")
