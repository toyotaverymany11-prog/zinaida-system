# Experimental Qwen Omni source checkpoint

Experimental and unqualified. The first GPU trial failed before inference. PyAV14.4.0 was changed to14.2.0 to use a binary wheel rather than an unsupported source build. No successful GPU inference is claimed.

The coordinator reports the own-server public cache complete:15files,22,378,997,960bytes, revision ae9e1690543ffd5c0221dc27f79834d0294cba00. Cache path: ../omni-public-cache/model. SHA256 values are pinned in model.lock.json; model weights are not part of this source checkpoint.

Before copying22GB to a paid GPU, run dependency_preflight.py with the EXACT actual interpreter. It imports torch, torchvision, torchaudio, av, soundfile, librosa, accelerate, both Qwen classes and process_mm_info. Package presence alone is insufficient; binary import and torch/torchaudio release/CUDA tags must match. In particular torch2.13+cu130 and torchaudio2.11 are not an assumed compatible pair. No weights or model inference are loaded by the preflight.

Install in a private venv only, preserve the CUDA image's matching Torch trio, and use --only-binary=:all: against official registries. av14.2.0 is pinned. requirements.txt contains the GPU preparation pins. This new whole environment has not yet passed a GPU test.

Run: timeout 60s ACTUAL_PY dependency_preflight.py --timeout-seconds 45 ; add --require-cuda only on an already allocated GPU. The result is dependency readiness, never artistic approval. evaluate.py performs this same preflight before from_pretrained.

Next GPU work is PUBLIC SYNTHETIC ONLY. Private film transfer remains blocked by approval review; this code does not override it. The root controller alone owns allocation,20minute deadline, export, deletion and total budget. No Pod is created by these files.

For two public inputs: ACTUAL_PY evaluate.py --model MODEL_DIR --lock model.lock.json --cases PUBLIC_CASES_JSON --output RESULT_JSON --deadline EPOCH. The cases JSON is exactly two objects {id,file,sha256}; do not include gold answers or scenario text. Two calls, one model load, raw audio,2fps,700output tokens and160seconds decoding per case, overall alarm, local_files_only, no remote code. No every-frame or frame-accurate lip-sync claim.

Do not redownload public HF weights on a paid GPU. Verify CPU cache first, then copy it only AFTER actual dependency imports pass. download_model.py is retained for explicit public CPU-cache maintenance.

A clean CPU-only dependency baseline may use torch2.8.0+cpu/torchvision0.23.0+cpu/torchaudio2.8.0+cpu. The mainserver Python3.13 requires numpy2.2.6 rather than the old Python3.12 GPU pin numpy1.26.4. Such a CPU smoke is not GPU/CUDA compatibility proof.
