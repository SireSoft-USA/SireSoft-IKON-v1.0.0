"""Offline contract tests for the real unified launcher (no server/GPU needed)."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app


def main():
    assert app.port_available('127.0.0.1', 0)
    with patch.object(app, 'detect_cuda', return_value=(True, 'Quadro P5000')):
        assert app.resolve_device('auto')[0] == 'cuda'
        assert app.resolve_device('cuda')[0] == 'cuda'
    with patch.object(app, 'detect_cuda', return_value=(False, 'driver unavailable')):
        assert app.resolve_device('auto')[0] == 'cpu'
        try:
            app.resolve_device('cuda')
        except RuntimeError as error:
            assert 'driver unavailable' in str(error)
        else:
            raise AssertionError('Strict GPU mode incorrectly falls back to CPU')
    assert app.resolve_device('cpu')[0] == 'cpu'
    args = SimpleNamespace(api_port=8010, web_port=5179, web_host='127.0.0.1')
    backend, frontend = app.build_commands(args, '/usr/bin/npm')
    assert 'runserver' in backend or 'gunicorn' in backend
    assert 'ikon_django.wsgi:application' in backend or 'manage.py' in ' '.join(backend)
    assert ['--port', '5179', '--strictPort'] == frontend[-3:]
    assert '--host' in frontend and '127.0.0.1' in frontend
    # Pure preflight: --check never starts a frontend or server process.
    with patch.object(app, 'detect_cuda', return_value=(True, 'Quadro P5000')):
        with patch.object(app.subprocess, 'Popen', side_effect=AssertionError('spawned service')):
            assert app.main(['--check', '--device', 'cuda']) == 0
    with patch.object(app, 'detect_cuda', return_value=(False, 'driver down')):
        assert app.main(['--check', '--gpu']) == 2
    vite = (ROOT / 'frontend/vite.config.ts').read_text(encoding='utf-8')
    assert 'SIREIKON_API_PORT' in vite
    assert "'/api'" in vite
    assert '127.0.0.1' in vite
    print('UNIFIED APP LAUNCHER TEST: PASS')


if __name__ == '__main__':
    main()
