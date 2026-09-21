# SireLLM Final Project Tests

This folder is the final repository-level validation layer.

Important: replace the previous `tests/` folder completely with this folder.
Do not merge old `repository_validator.py` or old manifest files into it.

## Commands

Repository-only diagnosis:

```bash
python tests/diagnose_repository.py
```

Final integration test:

```bash
python tests/test_system_integration.py
```

Curated cross-layer smoke suite:

```bash
python tests/run_all.py --smoke
```

All 116 mapped folder tests:

```bash
python tests/run_all.py --all
```

## Coverage model

Per-folder test coverage is no longer discovered with filesystem glob logic.
`system_manifest.py` contains an exact `TEST_FILE_BY_FOLDER` mapping for all
117 internal folders. This makes validation deterministic on Windows and
prevents false negatives for:

- `frontend/test_frontend_shell.py`
- `frontend/css/test_frontend_css.py`
- `frontend/js/test_frontend_js.py`
- `frontend/assets/test_frontend_assets.py`

The validator also avoids the regular-expression pattern that caused the
Python 3.10 `unterminated subpattern` error.
