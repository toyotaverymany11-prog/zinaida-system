"""Audio-driven LTX2.5 adaptation of the previously pinned Comfy graph.

Both samplers receive the original frozen audio latent. The final movie uses
the trimmed source waveform, never synthesized replacement speech.
"""
import copy
import json
import re
from pathlib import Path
from .contracts import Invalid, digest, sha

HERE = Path(__file__).parent
MODELS = {
    'unet': 'ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors',
    'clip': 'gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors',
    'video_vae': 'ltx-2.5-video-vae-bf16.safetensors',
    'audio_vae': 'ltx-2.5-audio-vae-bf16.safetensors',
    'upscaler': 'ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors',
}


def media_name(value, suffixes):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}\.[A-Za-z0-9]{2,5}', value):
        raise Invalid('Input must be an opaque local media basename')
    if Path(value).suffix.lower() not in suffixes:
        raise Invalid('Unexpected media type')
    return value


def build(prompt, image, image_sha256, audio, audio_sha256, *, seed=42, frames=129,
          width=768, height=1344, fps=24):
    media_name(image, {'.png', '.jpg', '.jpeg'})
    media_name(audio, {'.wav', '.mp3', '.flac'})
    sha(image_sha256); sha(audio_sha256)
    if not isinstance(prompt, str) or not 1 <= len(prompt) <= 16000:
        raise Invalid('Bounded scene direction required')
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
        raise Invalid('Invalid deterministic seed')
    if not all(type(x) is int for x in [width, height, fps, frames]):
        raise Invalid('Integer dimensions and timing required')
    if not (256 <= width <= 1536 and 256 <= height <= 1536 and width % 64 == 0
            and height % 64 == 0 and width * height <= 1048576):
        raise Invalid('Frame dimensions exceed qualified memory bounds')
    if fps != 24 or not 33 <= frames <= 241 or (frames - 1) % 8:
        raise Invalid('A2V trial requires24fps and8n+1frames within bounded length')
    graph = copy.deepcopy(json.loads((HERE/'workflows/ltx25-i2v.api.json').read_text()))
    graph['395']['inputs']['image'] = image
    graph['398:376']['inputs']['value'] = prompt
    graph['398:372'] = {'class_type': 'PrimitiveInt', 'inputs': {'value': width}}
    graph['398:360'] = {'class_type': 'PrimitiveInt', 'inputs': {'value': height}}
    graph.pop('403', None)
    graph['398:378'] = {'class_type': 'PrimitiveInt', 'inputs': {'value': frames}}
    # The replaced MathExpression exposed its integer on output1. PrimitiveInt
    # has only output0; retaining the old edge makes Comfy reject the prompt.
    graph['398:356']['inputs']['length'] = ['398:378', 0]
    graph['398:361']['inputs']['value'] = fps
    graph['398:339']['inputs']['noise_seed'] = seed
    graph['398:338']['inputs']['noise_seed'] = seed
    graph['398:384']['inputs']['unet_name'] = MODELS['unet']
    graph['398:397']['inputs']['sigmas'] = '1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0'
    graph['398:396']['inputs']['sigmas'] = '0.909375, 0.725, 0.421875, 0.0'
    graph.pop('398:366', None)
    graph.pop('398:358', None)
    graph.update({
        'sq_load_audio': {'class_type': 'LoadAudio', 'inputs': {'audio': audio}},
        'sq_trim_audio': {'class_type': 'TrimAudioDuration', 'inputs': {
            'audio': ['sq_load_audio', 0], 'start_index': 0, 'duration': frames/fps}},
        'sq_encode_audio': {'class_type': 'LTXVAudioVAEEncode', 'inputs': {
            'audio': ['sq_trim_audio', 0], 'audio_vae': ['398:386', 0]}},
        'sq_zero_noise': {'class_type': 'SolidMask', 'inputs': {'value': 0., 'width': 1024, 'height': 1024}},
        'sq_frozen_audio': {'class_type': 'SetLatentNoiseMask', 'inputs': {
            'samples': ['sq_encode_audio', 0], 'mask': ['sq_zero_noise', 0]}},
    })
    graph['398:377']['inputs']['audio_latent'] = ['sq_frozen_audio', 0]
    graph['398:340']['inputs']['audio_latent'] = ['sq_frozen_audio', 0]
    graph['398:370']['inputs']['audio'] = ['sq_trim_audio', 0]
    graph['75']['inputs']['filename_prefix'] = 'scene_quality/a2v'
    # Remove disconnected UI constants and fail on every dangling ancestor link.
    needed = set()
    def visit(key):
        if key in needed:
            return
        if key not in graph:
            raise Invalid('Dangling workflow reference: ' + key)
        needed.add(key)
        for value in graph[key]['inputs'].values():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                visit(value[0])
    visit('75')
    graph = {k: v for k, v in graph.items() if k in needed}
    binding = {'schema_version': 1, 'recipe': 'ltx25-a2v-internal-qualification',
               'image': {'name': image, 'sha256': image_sha256},
               'speech': {'name': audio, 'sha256': audio_sha256, 'frozen': True,
                          'output_uses_source_waveform': True},
               'format': {'width': width, 'height': height, 'fps': fps, 'frames': frames},
               'graph_sha256': digest(graph), 'status': 'prepared_gpu_unqualified',
               'artistic_approval': False, 'publication': False}
    return graph, binding


def check_runtime_nodes(graph, object_info):
    missing = sorted({n['class_type'] for n in graph.values()} - set(object_info))
    if missing:
        raise Invalid('Runtime lacks required nodes: ' + ','.join(missing))
    for node in graph.values():
        for name, value in node['inputs'].items():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                if value[0] not in graph:
                    raise Invalid('Runtime edge has no source: ' + name)
                outputs = object_info[graph[value[0]]['class_type']].get('output')
                if outputs is not None and (type(value[1]) is not int or not 0 <= value[1] < len(outputs)):
                    raise Invalid('Runtime output index does not exist: ' + value[0] + ':' + str(value[1]))
    return {'status': 'node_names_present_not_model_qualified'}
