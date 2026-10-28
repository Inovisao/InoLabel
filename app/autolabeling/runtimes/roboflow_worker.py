"""Standalone SAM 3 worker, executed by the optional Roboflow Python runtime."""

import json
import os
import sys
from importlib.metadata import PackageNotFoundError, version

PREFIX = 'INOLABEL_SAM3 '
MODEL_ID = 'sam3/sam3_final'
SDK_VERSION = '1.1.2'


def probe():
    packages = {}
    for package in ('inference-gpu', 'sam3', 'torch', 'torchvision'):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = None
    return {'python': list(sys.version_info[:3]), 'packages': packages}


def segment(model, request):
    from inference.core.entities.requests.sam3 import Sam3Prompt
    response = model.segment_image(
        image=request['image'],
        prompts=[Sam3Prompt(type='text', text=text) for text in request['prompts']],
        output_prob_thresh=request['score_threshold'],
        nms_iou_threshold=request['iou_threshold'], format='polygon',
    )
    return response.model_dump(mode='json', include={'prompt_results'})


def main():
    # SDK logs and errors may contain credentials; only the protocol reaches the app.
    output = sys.stdout
    sys.stdout = sys.stderr

    def send(payload):
        output.write(PREFIX + json.dumps(payload, allow_nan=False) + '\n')
        output.flush()

    info = probe()
    if '--probe' in sys.argv:
        send({'ok': True, 'runtime': info})
        return
    try:
        if info['packages']['inference-gpu'] != SDK_VERSION:
            raise RuntimeError('Unsupported SDK version')
        from inference.models.sam3 import SegmentAnything3
        model = SegmentAnything3(model_id=MODEL_ID, api_key=os.environ['ROBOFLOW_API_KEY'])
        artifacts = [model.cache_file(name) for name in model.get_infer_bucket_file_list()]
        send({'ok': True, 'runtime': info, 'artifacts': artifacts})
        if '--prepare' in sys.argv:
            return
        for line in sys.stdin:
            request = json.loads(line)
            if request.get('action') == 'close':
                return
            try:
                send({'ok': True, 'response': segment(model, request)})
            except Exception:
                send({'ok': False, 'stage': 'inference'})
    except Exception:
        send({'ok': False, 'stage': 'initialization'})


if __name__ == '__main__':
    main()
