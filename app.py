"""Convenience development launcher: Django API + unchanged React/Vite frontend.

For production use Gunicorn with ikon_django.wsgi:application behind Nginx.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / 'frontend'
HOST = os.getenv('SIRELLM_HOST', '127.0.0.1')
PORT = os.getenv('SIRELLM_PORT', '8000')


def main():
    npm = shutil.which('npm.cmd') or shutil.which('npm')
    if npm is None:
        raise SystemExit('npm is required for the React frontend; or run python manage.py runserver separately.')
    if not (FRONTEND / 'node_modules').is_dir():
        subprocess.run([npm, 'install'], cwd=FRONTEND, check=True)
    # Preflight is informational: preserve the model loader and frontend behavior.
    from ikon_django.core import _artifact_paths
    missing = {name: path for name, path in _artifact_paths().items()
               if not Path(path).is_file()}
    if missing:
        print('IKON MODEL NOT READY: required trained artifacts are missing locally:', file=sys.stderr)
        for name, path in missing.items():
            print(f'  {name}: {path}', file=sys.stderr)
        print('The source-only ZIP does not contain trained checkpoints, tokenizer or retrieval index.', file=sys.stderr)
        print('Django will run, but real chat replies require those model artifacts.', file=sys.stderr)
    frontend = subprocess.Popen([npm, 'run', 'dev'], cwd=FRONTEND)
    try:
        env = os.environ.copy()
        env.setdefault('SIREIKON_DEBUG', '1')
        print(f'SireSoft-IKON Django API: http://{HOST}:{PORT}')
        print('SireSoft-IKON React frontend: http://localhost:5173')
        subprocess.run([sys.executable, str(ROOT / 'manage.py'), 'runserver', '--noreload', f'{HOST}:{PORT}'],
                       cwd=ROOT, env=env, check=True)
    finally:
        if frontend.poll() is None:
            frontend.terminate()
            try:
                frontend.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend.kill()


if __name__ == '__main__':
    main()
