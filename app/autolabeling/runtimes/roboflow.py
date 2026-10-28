"""Roboflow runtime setup and a credential-free JSON protocol with a local worker."""

import json
import os
import subprocess
import sys
from pathlib import Path
from queue import Empty, Queue
from threading import Lock, Thread

from app import config as app_config
from app.api.common.errors import InvalidInput
from app.core.project_state.writer import write_json_atomic

SDK_VERSION = '1.1.2'
MODEL_ID = 'sam3/sam3_final'
PREFIX = 'INOLABEL_SAM3 '
preparation_lock = Lock()


def runtime_directory():
    return app_config.LOCAL_DIR / 'autolabeling' / 'runtimes' / 'sam3'


def executable():
    value = os.environ.get('INOLABEL_SAM3_PYTHON', '')
    path = Path(value).expanduser()
    if not value or not path.is_file() or not os.access(path, os.X_OK):
        raise InvalidInput('Configure INOLABEL_SAM3_PYTHON com o executável Python do ambiente SAM 3.')
    # Resolving a venv's Python symlink would select the base interpreter instead.
    return path.absolute()


def worker_command(mode):
    if getattr(sys, 'frozen', False):
        worker = Path(sys._MEIPASS) / 'app' / 'autolabeling' / 'runtimes' / 'roboflow_worker.py'
    else:
        worker = Path(__file__).with_name('roboflow_worker.py')
    return [str(executable()), '-u', str(worker), mode]


def worker_environment():
    env = os.environ.copy()
    env['MODEL_CACHE_DIR'] = str(runtime_directory() / 'cache')
    # Do not inherit a frozen application's Python path into an external interpreter.
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    return env


def decode_message(line):
    if line.startswith(PREFIX):
        return json.loads(line[len(PREFIX):])
    return None


def runtime_info():
    try:
        result = subprocess.run(worker_command('--probe'), env=worker_environment(),
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, timeout=15, check=True)
        message = next((decode_message(line) for line in result.stdout.splitlines() if line.startswith(PREFIX)), None)
        info = message['runtime'] if message and message.get('ok') else None
    except (OSError, subprocess.SubprocessError, ValueError, KeyError):
        info = None
    expected = {'inference-gpu': SDK_VERSION, 'sam3': '0.1.3', 'torch': '2.8.0', 'torchvision': '0.23.0'}
    if not info or any((info['packages'].get(name) or '').split('+')[0] != value for name, value in expected.items()):
        raise InvalidInput('Instale requirements-sam3.txt no ambiente indicado por INOLABEL_SAM3_PYTHON (Python 3.12 recomendado).')
    return info


def artifact_record(path):
    path = Path(path).resolve()
    cache = (runtime_directory() / 'cache').resolve()
    if cache not in path.parents:
        raise InvalidInput('O runtime retornou um cache fora do diretório configurado.')
    stat = path.stat()
    if not path.is_file() or stat.st_size == 0:
        raise InvalidInput('Os pesos do SAM 3 estão incompletos. Prepare o modelo novamente.')
    return {'path': str(path), 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}


def prepared_record(info):
    try:
        data = json.loads((runtime_directory() / 'prepared.json').read_text(encoding='utf-8'))
        runtime_stat = executable().stat()
        if (data['model_id'] != MODEL_ID or data['runtime'] != info
                or data['python'] != str(executable()) or data['python_mtime_ns'] != runtime_stat.st_mtime_ns
                or len(data['artifacts']) != 2
                or any(artifact_record(a['path']) != a for a in data['artifacts'])):
            raise ValueError('Runtime or cache changed')
        return data
    except (OSError, ValueError, KeyError, TypeError):
        raise InvalidInput('Prepare o SAM 3 para baixar e validar os pesos nesta instalação.')


def status(model_id=None):
    reasons = []
    snapshot = None
    try:
        executable()
        snapshot = prepared_record(runtime_info())
    except InvalidInput as exc:
        reasons.append(str(exc))
    return {'reasons': reasons, 'snapshot': snapshot}


class WorkerClient:
    def __init__(self, mode='--serve', timeout=600):
        self.process = None
        self.messages = Queue()
        if not os.environ.get('ROBOFLOW_API_KEY'):
            raise InvalidInput('Configure ROBOFLOW_API_KEY no servidor, sem salvar a chave no projeto.')
        try:
            self.process = subprocess.Popen(worker_command(mode), env=worker_environment(),
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.DEVNULL, text=True, bufsize=1)
            Thread(target=self._read, args=(self.process.stdout,), daemon=True).start()
            self.ready = self.receive(timeout)
        except (OSError, InvalidInput):
            self.close()
            raise InvalidInput('Não foi possível inicializar o SAM 3. Verifique o runtime, a chave, o acesso aos pesos e a memória disponível.')

    def _read(self, stream):
        try:
            for line in stream:
                try:
                    value = decode_message(line)
                except ValueError:
                    continue
                if value is not None:
                    self.messages.put(value)
        except (OSError, ValueError):
            pass
        finally:
            self.messages.put(None)

    def receive(self, timeout):
        try:
            message = self.messages.get(timeout=timeout)
        except Empty:
            self.close()
            raise InvalidInput('O SAM 3 excedeu o tempo limite. Verifique o runtime e os recursos disponíveis.')
        if not message or not message.get('ok'):
            raise InvalidInput('O runtime SAM 3 falhou. Verifique dependências, acesso ao modelo e memória disponível.')
        return message

    def predict(self, image, prompts, score_threshold, iou_threshold):
        if self.process is None or self.process.poll() is not None:
            raise InvalidInput('O runtime SAM 3 foi encerrado. Retome a execução para tentar novamente.')
        try:
            self.process.stdin.write(json.dumps({'action': 'predict', 'image': str(image), 'prompts': prompts,
                                                 'score_threshold': score_threshold, 'iou_threshold': iou_threshold}) + '\n')
            self.process.stdin.flush()
            return self.receive(600)['response']
        except (OSError, ValueError, KeyError):
            self.close()
            raise InvalidInput('Falha na comunicação com o runtime SAM 3.')

    def close(self):
        process = self.process
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for stream in (process.stdin, process.stdout):
            if stream:
                stream.close()
        self.process = None


def prepare():
    if not preparation_lock.acquire(blocking=False):
        raise InvalidInput('O SAM 3 já está sendo preparado. Aguarde a conclusão.')
    client = None
    try:
        info = runtime_info()
        client = WorkerClient('--prepare', timeout=1800)
        artifacts = [artifact_record(path) for path in client.ready['artifacts']]
        if len(artifacts) != 2:
            raise InvalidInput('O download dos pesos SAM 3 não foi concluído.')
        write_json_atomic(runtime_directory() / 'prepared.json', {
            'model_id': MODEL_ID, 'runtime': info, 'python': str(executable()),
            'python_mtime_ns': executable().stat().st_mtime_ns, 'artifacts': artifacts,
        })
    finally:
        if client:
            client.close()
        preparation_lock.release()


def open_worker():
    prepared_record(runtime_info())
    return WorkerClient()
