"""Local Ollama vision-language adapter for prompt-driven box proposals."""

import base64
import ipaddress
import json
import math
import urllib.error
import urllib.request
from urllib.parse import urlsplit

import cv2

from app.api.common.errors import InvalidInput
from app.autolabeling.model_catalog.ollama_inputs import OllamaInputs


MAX_INFERENCE_PIXELS = 1_500_000


class OllamaAdapter:
    def __init__(self, model):
        self.model = model

    def inspect(self):
        return {}

    def predict(self, image, config, classes):
        inputs = OllamaInputs.model_validate(config.parameters)
        prompts = inputs.class_prompts
        if any(item.class_name not in classes for item in prompts):
            raise InvalidInput('A prompt class is no longer present in this project.')
        inference_image = _fit_pixel_budget(image, MAX_INFERENCE_PIXELS)
        ok, encoded = cv2.imencode('.jpg', inference_image)
        if not ok:
            raise InvalidInput('Could not encode image for Ollama.')
        schema = {
            'type': 'object',
            'properties': {'detections': {'type': 'array', 'items': {
                'type': 'object', 'properties': {'class_name': {'type': 'string'},
                    'bbox': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 4, 'maxItems': 4},
                    'confidence': {'type': 'number'}},
                'required': ['class_name', 'bbox', 'confidence'], 'additionalProperties': False,
            }}},
            'required': ['detections'], 'additionalProperties': False,
        }
        prompt_text = json.dumps({'instruction': inputs.instruction,
            'objects': [{'class_name': p.class_name, 'description': p.text} for p in prompts],
            'image_size': {'width': inference_image.shape[1], 'height': inference_image.shape[0]},
            'coordinates': 'bbox is [x_min,y_min,x_max,y_max], normalized to 0..1000.'}, ensure_ascii=False)
        request = urllib.request.Request(f'{ollama_base_url()}/api/chat', data=json.dumps({
            'model': self.model, 'stream': False, 'format': schema,
            'messages': [{'role': 'user', 'content': prompt_text, 'images': [base64.b64encode(encoded).decode('ascii')]}],
            # Vision-language models such as Qwen3-VL may otherwise return only a
            # reasoning channel, leaving message.content empty for structured output.
            'think': False,
            # Qwen3-VL can spend over 1k tokens in its internal reasoning on
            # harder images before producing the schema-constrained answer.
            'options': {'temperature': 0, 'num_ctx': 8192, 'num_predict': 3072},
        }).encode(), headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                payload = json.loads(response.read())
            message = payload.get('message') or {}
            content = message.get('content', '')
            if payload.get('done_reason') == 'length':
                raise InvalidInput('Ollama reached its context or generation limit before returning complete detection JSON. The inference image was resized; use shorter object descriptions or a model with more context.')
            if not isinstance(content, str) or not content.strip():
                if message.get('thinking'):
                    raise InvalidInput('Ollama returned reasoning but no detection JSON. This model did not follow the structured detection format.')
                raise InvalidInput('Ollama returned an empty response. Check the Ollama server log and model compatibility with structured output.')
            output = json.loads(content)
        except urllib.error.HTTPError as exc:
            detail = _ollama_error_detail(exc.read())
            if exc.code == 404:
                message = f"Ollama could not find model '{self.model}'. Download it with `ollama pull {self.model}`."
            elif detail:
                message = f'Ollama inference failed (HTTP {exc.code}): {detail}'
            else:
                message = f'Ollama inference failed (HTTP {exc.code}). Check the Ollama server log.'
            raise InvalidInput(message) from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, 'reason', None)
            if isinstance(reason, (ConnectionError, TimeoutError, OSError)):
                message = 'Could not connect to Ollama at the configured local address. Start Ollama and try again.'
            else:
                message = f'Ollama request failed: {_ollama_error_detail(reason) or "check the local server"}.'
            raise InvalidInput(message) from exc
        except (OSError, ValueError, KeyError, TypeError) as exc:
            if 'payload' in locals() and payload.get('done_reason') == 'length':
                raise InvalidInput('Ollama reached its context or generation limit before returning complete detection JSON. The inference image was resized; use shorter object descriptions or a model with more context.') from exc
            detail = _ollama_error_detail(exc)
            raise InvalidInput(f'Ollama returned an invalid response: {detail or type(exc).__name__}.') from exc
        if set(output) != {'detections'} or not isinstance(output['detections'], list):
            raise InvalidInput('Ollama returned an invalid detection response.')
        height, width = image.shape[:2]
        mapping = {p.class_name: (classes.index(p.class_name), p.text) for p in prompts}
        predictions = []
        for item in output['detections']:
            if not isinstance(item, dict) or set(item) != {'class_name', 'bbox', 'confidence'}:
                raise InvalidInput('Ollama returned an invalid detection entry.')
            if item['class_name'] not in mapping or not isinstance(item['bbox'], list) or len(item['bbox']) != 4:
                raise InvalidInput('Ollama returned an unknown class or invalid box.')
            try:
                x1, y1, x2, y2 = [float(value) for value in item['bbox']]
                score = float(item['confidence'])
            except (TypeError, ValueError):
                raise InvalidInput('Ollama returned invalid coordinates or confidence.') from None
            if not all(math.isfinite(x) for x in (x1, y1, x2, y2, score)) or not 0 <= score <= 1:
                raise InvalidInput('Ollama returned non-finite coordinates or confidence.')
            x1, x2 = max(0., min(x1, 1000)) * width / 1000, max(0., min(x2, 1000)) * width / 1000
            y1, y2 = max(0., min(y1, 1000)) * height / 1000, max(0., min(y2, 1000)) * height / 1000
            if x2 > x1 and y2 > y1:
                category_id, _ = mapping[item['class_name']]
                predictions.append((category_id, [x1, y1, x2-x1, y2-y1], score))
        return predictions


def ollama_base_url():
    import os
    value = os.environ.get('OLLAMA_HOST', '127.0.0.1:11434').rstrip('/')
    parsed = urlsplit(value if '://' in value else 'http://' + value)
    try:
        address = ipaddress.ip_address(parsed.hostname or '')
        local = address.is_loopback or address.is_unspecified
    except ValueError:
        local = (parsed.hostname or '').lower() == 'localhost'
    if parsed.scheme != 'http' or not local or parsed.username or parsed.password or parsed.path:
        raise InvalidInput('OLLAMA_HOST must point to a local Ollama server.')
    host = '127.0.0.1' if parsed.hostname in ('0.0.0.0', '::') else parsed.hostname
    return f'http://{host}:{parsed.port or 11434}'


def _fit_pixel_budget(image, max_pixels):
    height, width = image.shape[:2]
    pixels = width * height
    if pixels <= max_pixels:
        return image
    scale = math.sqrt(max_pixels / pixels)
    resized_width = max(1, round(width * scale))
    resized_height = max(1, round(height * scale))
    while resized_width * resized_height > max_pixels:
        if resized_width / width >= resized_height / height:
            resized_width -= 1
        else:
            resized_height -= 1
    return cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_AREA)


def _ollama_error_detail(value):
    if isinstance(value, bytes):
        value = value.decode('utf-8', errors='replace')
    try:
        payload = json.loads(value) if isinstance(value, str) else None
        if isinstance(payload, dict):
            value = payload.get('error') or payload.get('message') or value
    except ValueError:
        pass
    detail = ' '.join(str(value).split())
    return detail[:300] if detail else ''
