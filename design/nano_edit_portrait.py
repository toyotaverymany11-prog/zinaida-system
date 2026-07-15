#!/usr/bin/env python3
"""Nano Banana 2: Edit Zinaida portrait with text overlay"""
import os, json, base64, sys
import requests
import replicate

# Read token
with open('/opt/zinaida/dizayner/replicate_config.json') as f:
    cfg = json.load(f)
token = cfg['api_token']
os.environ['REPLICATE_API_TOKEN'] = token

# Read the image and convert to base64 data URI
image_path = '/opt/zinaida/design/generated/lera_test/10_portrait_v3.jpg'
with open(image_path, 'rb') as f:
    image_data = f.read()
    b64 = base64.b64encode(image_data).decode('utf-8')
    data_uri = f"data:image/jpeg;base64,{b64}"

print(f"Original image size: {len(image_data)} bytes")
print(f"Base64 data URI length: {len(data_uri)} chars")
print(f"Data URI prefix: {data_uri[:50]}...")

# Prompt from the task with actual Cyrillic text
prompt = (
    "Add Russian Cyrillic text "
    "'\u041c\u0415\u0413\u0410\u041c\u041e\u0417\u0413' "
    "in large elegant font to the top of this image, text "
    "'AI-\u0430\u043d\u0430\u043b\u0438\u0442\u0438\u043a \u043c\u0443\u0436\u0441\u043a\u043e\u0439 \u043f\u0441\u0438\u0445\u043e\u043b\u043e\u0433\u0438\u0438' "
    "at bottom. Text must look physically part of the image. "
    "Keep the woman's face exactly the same as original. "
    "Black and white editorial style. "
    "No date No barcode No extra text"
)

print("\n=== Calling replicate.run for google/nano-banana-2 ===")
print(f"Prompt: {prompt}")
print(f"image_input as array with 1 item (data URI)")

try:
    output = replicate.run(
        "google/nano-banana-2",
        input={
            "prompt": prompt,
            "image_input": [data_uri],  # ARRAY with one data URI string
            "aspect_ratio": "match_input_image",
            "resolution": "1K",
            "output_format": "png"
        }
    )
    print(f"\nOutput type: {type(output).__name__}")
    print(f"Output: {output}")
    
    if output:
        output_url = str(output)
        print(f"\nDownloading from: {output_url}")
        img_resp = requests.get(output_url)
        if img_resp.status_code == 200:
            save_path = '/opt/zinaida/design/generated/lera_test/G3_nano_edit.png'
            with open(save_path, 'wb') as f:
                f.write(img_resp.content)
            print(f"Saved to: {save_path}")
            print(f"Size: {len(img_resp.content)} bytes")
        else:
            print(f"Download failed: HTTP {img_resp.status_code}")
    else:
        print("Output is empty/None")
        
except Exception as e:
    err = str(e)
    print(f"Error: {err[:500]}")
    sys.exit(1)
