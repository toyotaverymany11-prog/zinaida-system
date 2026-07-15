import replicate, os, json, urllib.request, time

os.environ["REPLICATE_API_TOKEN"] = "r8_FfocPxC0MCo8MXleqrPNmA9H3bWTByz3qODgt"

ANGLES = [
    {"name": "front_thoughtful", "suffix": "front view, thoughtful pensive expression, looking slightly up"},
    {"name": "right_profile", "suffix": "right profile view, 90 degree side"},
    {"name": "three_quarter_right_serious", "suffix": "three quarter view from right, determined expression"},
    {"name": "three_quarter_left_smile", "suffix": "three quarter view from left, soft smile"},
    {"name": "three_quarter_right_smile", "suffix": "three quarter view from right, gentle smile"},
    {"name": "three_quarter_left_thoughtful", "suffix": "three quarter view from left, deep in thought"},
    {"name": "slight_left_intense", "suffix": "slight left turn, intense focused gaze"},
    {"name": "slight_right_soft", "suffix": "slight right turn, soft relaxed expression"},
    {"name": "chin_up_confident", "suffix": "chin slightly raised, confident powerful expression"},
    {"name": "chin_down_mysterious", "suffix": "chin lowered, mysterious alluring look through lashes"},
    {"name": "over_shoulder_left", "suffix": "looking over left shoulder, elegant pose"},
    {"name": "over_shoulder_right", "suffix": "looking over right shoulder, casual glance back"},
    {"name": "laughing", "suffix": "genuine laughing expression, authentic joy, eyes crinkling"},
    {"name": "contemplative_window", "suffix": "looking out window, contemplative mood, natural side light"},
    {"name": "close_up_eyes", "suffix": "extreme close-up eyes and upper face, piercing direct gaze"},
]

BASE = "Professional portrait photo of young woman 28yo, dark hair, Slavic features from Sochi Russia. Ultra-realistic skin with visible pores, natural imperfections, subsurface scattering. Shot Canon EOS R5 85mm f1.4. 8K photorealistic. "
output_dir = "/opt/zinaida/design/passport/"

existing = json.load(open(os.path.join(output_dir, "face_passport.json")))
passport = existing.get("angles", [])
start_idx = len(passport)

for i, a in enumerate(ANGLES):
    idx = start_idx + i + 1
    prompt = BASE + a["suffix"]
    print(f"[{idx}/20] {a['name']}...")
    try:
        out = replicate.run("black-forest-labs/flux-dev", input={"prompt": prompt, "guidance": 3.5, "num_inference_steps": 28, "width": 1024, "height": 1024, "output_format": "png"})
        url = out[0] if isinstance(out, list) else str(out)
        fn = f"passport_{idx:02d}_{a['name']}.png"
        fp = os.path.join(output_dir, fn)
        urllib.request.urlretrieve(url, fp)
        passport.append({"index": idx, "name": a["name"], "filename": fn, "prompt": prompt, "path": fp})
        sz = os.path.getsize(fp)
        print(f"  OK: {fn} ({sz} bytes)")
        time.sleep(2)
    except Exception as e:
        print(f"  ERROR: {e}")
        passport.append({"index": idx, "name": a["name"], "error": str(e)})
        time.sleep(5)

with open(os.path.join(output_dir, "face_passport.json"), "w") as f:
    json.dump({"subject": "Зинаида", "total": 20, "ok": len([p for p in passport if "filename" in p]), "failed": len([p for p in passport if "error" in p]), "reference_photos": ["/opt/zinaida/SmmFabrika/queue/111/IMG_0413.PNG", "/opt/zinaida/SmmFabrika/queue/111/IMG_0415.PNG", "/opt/zinaida/SmmFabrika/queue/111/IMG_9391.JPG"], "angles": passport}, f, ensure_ascii=False, indent=2)
print(f"\nDONE: {len([p for p in passport if 'filename' in p])}/20 angles")
