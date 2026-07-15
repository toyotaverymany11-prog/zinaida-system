# Successful Generations — 12 July 2026

## Reference Card: Complete text-behind-subject with Cyrillic

### Winning Prompt
```
Premium fashion magazine cover. Bold white serif Cyrillic letters spelling ЧУЖОЙ 
as giant letters across the image: letter Ч at top left overlapping her forehead, 
letter У over head, letter Ж at right, letter О over shoulder, letter Й at bottom 
right. Letters are woven with the woman face, some in front some behind creating depth. 
Small white serif text on left: СИЛА ПРИТЯЖЕНИЯ КОГДА ХИМИЯ ГРОМЧЕ СЛОВ. 
Small text on right: НЕУЛОВИМОЕ ПРИСУТСТВИЕ ИСТОРИЯ ОДНОГО СЛЕДА. 
Large letter З at bottom left. Text at bottom: ПРАВДА КОТОРУЮ НЕЛЬЗЯ ИГНОРИРОВАТЬ. 
The woman: young Russian woman 28 years old, oval face with subtle asymmetry, 
ice blue almond-shaped eyes, straight nose with slight bump on bridge, full lips 
lower lip fuller, naturally thick arched eyebrows, dark brown hair NOT blonde, 
fair skin with warm undertone, serious confident expression. 
Deep black background. One large textured dark red brushstroke accent. 
Dramatic side lighting, high contrast, Vogue editorial aesthetic. 
CRITICAL: all Cyrillic text must be correct Russian Cyrillic no errors no Latin letters.
```

### Parameters
- **Model:** `fal-ai/gpt-image-2`
- **Service:** FAL.ai (via curl queue API)
- **Format:** 1080×1350 (4:5 portrait)
- **Cost:** $0.04-0.06
- **Time:** 128 seconds
- **Queue ID:** `019f567f-9690-7ad1-b926-6908a03db1bc`
- **Result URL:** `https://v3b.fal.media/files/b/0aa1f562/_TeJRuy_cn9kBWRttsG5C_8mjwzkXG.png`

### Verification (vision_analyze)
- ЧУЖОЙ: correct, all 5 letters are proper Cyrillic
- Left text: СИЛА ПРИТЯЖЕНИЯ КОГДА ХИМИЯ ГРОМЧЕ СЛОВ — correct
- Right text: НЕУЛОВИМОЕ ПРИСУТСТВИЕ ИСТОРИЯ ОДНОГО СЛЕДА — correct
- Bottom: ПРАВДА КОТОРУЮ НЕЛЬЗЯ ИГНОРИРОВАТЬ — correct
- Face: dark hair, ice blue eyes, matches Zinaida description
- Style: text-behind-subject, letters woven with face
- Quality: 9/10

### What Worked
1. **All Cyrillic text in one prompt** — GPT Image 2 handles long multi-line Russian perfectly
2. **Individual letter positions** — explicitly describing Ч У Ж О Й placement helped the model integrate them with the face
3. **Detailed face description** — the full Zinaida description (slight nose bump, asymmetrical lips, ice blue eyes) was critical
4. **Black + white + single accent** — strict 3-color palette

### What Failed Before
1. Ideogram V3 Turbo: mixed Cyrillic/Latin, misspellings (ЦУТОПОЙ, ЗАРАХ, мучий, отдаликивать)
2. GPT Image 2 + image_url (img2img): mixing an existing face with text caused Cyrillic breakdown (Ч→U, Ж→X)
3. GPT Image 2 без детального описания: получалась blonde женщина (как на референсе), не Зинаида

### Key Lesson
**GPT Image 2 + full text prompt + detailed face description = best results for text-behind-subject with Cyrillic.**
FLUX LoRA is NOT needed if the text description is precise enough — GPT Image 2 generates a face close enough to Zinaida.
The `image_url` parameter should be avoided; always generate from scratch with one prompt.
