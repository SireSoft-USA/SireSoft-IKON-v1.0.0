from pathlib import Path
import shutil
import sys

ROOT = Path.cwd()
TESTS = ROOT / "tests"
TARGET = TESTS / "repository_validator.py"

if not TARGET.is_file():
    raise SystemExit(
        "Could not find tests/repository_validator.py. "
        "Run this script from the SireLLM project root."
    )

source = r"""
import ast
import json
import re
import sys
from pathlib import Path


class RepositoryValidator:
    def __init__(
        self,
        root,
        expected_folders,
        critical_files,
    ):
        self.root = Path(root).resolve()
        self.expected_folders = tuple(expected_folders)
        self.critical_files = tuple(critical_files)

    def validate_structure(self):
        missing_folders = []
        missing_files = []

        for relative in self.expected_folders:
            if not (self.root / relative).is_dir():
                missing_folders.append(relative)

        for relative in self.critical_files:
            if not (self.root / relative).is_file():
                missing_files.append(relative)

        return {
            "expected_folder_count": len(self.expected_folders),
            "missing_folders": missing_folders,
            "missing_files": missing_files,
            "valid": (
                len(missing_folders) == 0
                and len(missing_files) == 0
            ),
        }

    def validate_folder_test_coverage(self):
        uncovered = []
        covered = []

        explicit_tests = {
            "frontend": (
                "test_frontend_shell.py",
            ),
            "frontend/css": (
                "test_frontend_css.py",
            ),
            "frontend/js": (
                "test_frontend_js.py",
            ),
            "frontend/assets": (
                "test_frontend_assets.py",
            ),
            "tools": (
                "test_tools.py",
            ),
            "tests": (
                "test_system_integration.py",
            ),
        }

        for relative in self.expected_folders:
            folder = self.root / relative

            direct_tests = []

            if folder.is_dir():
                for path in folder.iterdir():
                    if (
                        path.is_file()
                        and path.suffix.lower() == ".py"
                        and path.name.lower().startswith("test_")
                    ):
                        direct_tests.append(path.name)

            direct_tests = sorted(direct_tests)
            required = explicit_tests.get(relative)

            if required is not None:
                missing_required = [
                    filename
                    for filename in required
                    if not (folder / filename).is_file()
                ]

                if missing_required:
                    uncovered.append(relative)
                else:
                    covered.append({
                        "folder": relative,
                        "tests": sorted(
                            set(
                                direct_tests
                                + list(required)
                            )
                        ),
                    })

                continue

            if len(direct_tests) == 0:
                uncovered.append(relative)
            else:
                covered.append({
                    "folder": relative,
                    "tests": direct_tests,
                })

        return {
            "covered_folder_count": len(covered),
            "uncovered_folders": uncovered,
            "valid": len(uncovered) == 0,
        }

    def validate_python_imports(self):
        python_files = sorted(
            self.root.rglob("*.py")
        )

        stdlib = set(
            getattr(
                sys,
                "stdlib_module_names",
                (),
            )
        )

        top_level_roots = {
            path.name
            for path in self.root.iterdir()
            if path.is_dir()
        }

        local_module_names = {
            path.stem
            for path in python_files
        }

        external = set()
        parse_errors = []

        for path in python_files:
            relative = (
                path.relative_to(self.root)
                .as_posix()
            )

            try:
                tree = ast.parse(
                    path.read_text(
                        encoding="utf-8"
                    ),
                    filename=relative,
                )
            except Exception as error:
                parse_errors.append({
                    "path": relative,
                    "error": str(error),
                })
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [
                        alias.name
                        for alias in node.names
                    ]

                elif isinstance(node, ast.ImportFrom):
                    if node.level > 0:
                        continue

                    names = (
                        [node.module]
                        if node.module
                        else []
                    )

                else:
                    continue

                for name in names:
                    root_name = name.split(".")[0]

                    if (
                        root_name in stdlib
                        or root_name in top_level_roots
                        or root_name in local_module_names
                    ):
                        continue

                    external.add(root_name)

        return {
            "python_file_count": len(python_files),
            "external_roots": sorted(external),
            "parse_errors": parse_errors,
            "valid": (
                len(external) == 0
                and len(parse_errors) == 0
            ),
        }

    def validate_frontend_contract(self):
        html = (
            self.root
            / "frontend/index.html"
        ).read_text(
            encoding="utf-8"
        )

        css = (
            self.root
            / "frontend/css/app.css"
        ).read_text(
            encoding="utf-8"
        )

        js = (
            self.root
            / "frontend/js/api.js"
        ).read_text(
            encoding="utf-8"
        )

        manifest = json.loads(
            (
                self.root
                / "frontend/assets/asset_manifest.json"
            ).read_text(
                encoding="utf-8"
            )
        )

        html_remote = re.compile(
            "(?:src|href)=[\\\"']https?://",
            re.IGNORECASE,
        )

        css_remote = re.compile(
            "url\\\\(\\\\s*[\\\"']?https?://",
            re.IGNORECASE,
        )

        checks = {
            "local_css": "./css/app.css" in html,
            "local_js": "./js/app.js" in html,
            "health_route": '"/v1/health"' in js,
            "chat_route": '"/v1/chat"' in js,
            "responsive_css": (
                "@media (max-width: 640px)"
                in css
            ),
            "assets_declared": (
                len(
                    manifest.get(
                        "assets",
                        [],
                    )
                )
                >= 4
            ),
            "no_html_cdn": (
                html_remote.search(html)
                is None
            ),
            "no_css_remote_assets": (
                css_remote.search(css)
                is None
            ),
        }

        return {
            "checks": checks,
            "valid": all(checks.values()),
        }

    def validate_gateway_contract(self):
        source = (
            self.root
            / "services/api_gateway/routes.py"
        ).read_text(
            encoding="utf-8"
        )

        required_routes = (
            "/v1/chat",
            "/v1/generate",
            "/v1/retrieve",
            "/v1/embed",
            "/v1/health",
        )

        missing = [
            route
            for route in required_routes
            if route not in source
        ]

        return {
            "required_route_count": len(required_routes),
            "missing_routes": missing,
            "valid": len(missing) == 0,
        }

    def validate_all(self):
        structure = self.validate_structure()
        coverage = self.validate_folder_test_coverage()
        imports = self.validate_python_imports()
        frontend = self.validate_frontend_contract()
        gateway = self.validate_gateway_contract()

        return {
            "structure": structure,
            "folder_test_coverage": coverage,
            "imports": imports,
            "frontend": frontend,
            "gateway": gateway,
            "valid": all((
                structure["valid"],
                coverage["valid"],
                imports["valid"],
                frontend["valid"],
                gateway["valid"],
            )),
        }
"""

backup = TESTS / "repository_validator.py.bak"
if not backup.exists():
    shutil.copy2(TARGET, backup)

TARGET.write_text(source.lstrip(), encoding="utf-8")

print("Replaced:", TARGET)
print("Backup:", backup)
print()
print("Now run:")
print("  python tests/diagnose_repository.py")
print("  python tests/test_system_integration.py")
