import ast
import json
import sys
from pathlib import Path


class RepositoryValidator:
    def __init__(
        self,
        root,
        expected_folders,
        critical_files,
        test_file_by_folder,
    ):
        self.root = Path(root).resolve()
        self.expected_folders = tuple(
            expected_folders
        )
        self.critical_files = tuple(
            critical_files
        )
        self.test_file_by_folder = dict(
            test_file_by_folder
        )

    def validate_structure(self):
        missing_folders = []
        missing_files = []

        for relative in self.expected_folders:
            if not (
                self.root / relative
            ).is_dir():
                missing_folders.append(
                    relative
                )

        for relative in self.critical_files:
            if not (
                self.root / relative
            ).is_file():
                missing_files.append(
                    relative
                )

        return {
            "expected_folder_count": len(
                self.expected_folders
            ),
            "missing_folders": (
                missing_folders
            ),
            "missing_files": (
                missing_files
            ),
            "valid": (
                not missing_folders
                and not missing_files
            ),
        }

    def validate_folder_test_coverage(self):
        uncovered = []
        covered = []
        manifest_errors = []

        expected_set = set(
            self.expected_folders
        )

        mapped_set = set(
            self.test_file_by_folder
        )

        missing_mappings = sorted(
            expected_set - mapped_set
        )

        extra_mappings = sorted(
            mapped_set - expected_set
        )

        if missing_mappings:
            manifest_errors.append({
                "kind": "missing_test_mapping",
                "folders": missing_mappings,
            })

        if extra_mappings:
            manifest_errors.append({
                "kind": "unknown_test_mapping",
                "folders": extra_mappings,
            })

        for relative in self.expected_folders:
            test_relative = (
                self.test_file_by_folder
                .get(
                    relative
                )
            )

            if not test_relative:
                uncovered.append(
                    relative
                )
                continue

            test_path = (
                self.root
                / test_relative
            )

            if (
                test_path.is_file()
                and test_path.suffix.lower()
                == ".py"
                and test_path.name.lower()
                .startswith(
                    "test_"
                )
            ):
                covered.append({
                    "folder": relative,
                    "test_file": (
                        test_relative
                    ),
                })
            else:
                uncovered.append(
                    relative
                )

        return {
            "covered_folder_count": len(
                covered
            ),
            "uncovered_folders": (
                uncovered
            ),
            "manifest_errors": (
                manifest_errors
            ),
            "valid": (
                not uncovered
                and not manifest_errors
                and len(
                    covered
                )
                == len(
                    self.expected_folders
                )
            ),
        }

    def validate_python_imports(self):
        python_files = sorted(
            self.root.rglob("*.py")
        )

        stdlib = set(
            getattr(sys, "stdlib_module_names", ())
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

        # These are existing application/runtime dependencies, not ML/compute
        # dependencies. The no-library ML constraint is enforced separately.
        allowed_runtime_roots = {
            "fastapi",
            "pydantic",
            "uvicorn",
        }

        forbidden_ml_roots = {
            "torch",
            "tensorflow",
            "numpy",
            "cupy",
            "numba",
            "jax",
            "scipy",
            "sklearn",
            "transformers",
            "keras",
        }

        external = set()
        allowed_external = set()
        forbidden_found = set()
        parse_errors = []

        for path in python_files:
            relative = path.relative_to(self.root).as_posix()

            try:
                tree = ast.parse(
                    path.read_text(encoding="utf-8"),
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
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level > 0:
                        continue
                    names = [node.module] if node.module else []
                else:
                    continue

                for name in names:
                    root_name = name.split(".")[0]

                    if root_name in forbidden_ml_roots:
                        forbidden_found.add(root_name)
                        continue

                    if (
                        root_name in stdlib
                        or root_name in top_level_roots
                        or root_name in local_module_names
                    ):
                        continue

                    if root_name in allowed_runtime_roots:
                        allowed_external.add(root_name)
                        continue

                    external.add(root_name)

        return {
            "python_file_count": len(python_files),
            "external_roots": sorted(external),
            "allowed_external_roots": sorted(allowed_external),
            "forbidden_ml_roots": sorted(forbidden_found),
            "parse_errors": parse_errors,
            "valid": (
                not external
                and not forbidden_found
                and not parse_errors
            ),
        }

    @staticmethod
    def _html_has_remote_reference(
        html,
    ):
        compact = "".join(
            html.lower().split()
        )

        markers = (
            'src="http://',
            "src='http://",
            'src="https://',
            "src='https://",
            'href="http://',
            "href='http://",
            'href="https://',
            "href='https://",
        )

        return any(
            marker in compact
            for marker in markers
        )

    @staticmethod
    def _css_has_remote_asset(
        css,
    ):
        compact = "".join(
            css.lower().split()
        )

        markers = (
            "url(http://",
            "url(https://",
            'url("http://',
            'url("https://',
            "url('http://",
            "url('https://",
            "@importurl(http://",
            "@importurl(https://",
            '@import"url(http://',
            '@import"url(https://',
        )

        return any(
            marker in compact
            for marker in markers
        )

    def validate_frontend_contract(self):
        frontend = self.root / "frontend"
        index_html = frontend / "index.html"
        package_json = frontend / "package.json"
        vite_config = frontend / "vite.config.ts"
        main_tsx = frontend / "src/main.tsx"
        app_tsx = frontend / "src/App.tsx"
        index_css = frontend / "src/index.css"
        api_ts = frontend / "src/lib/api.ts"
        components_dir = frontend / "src/components"
        public_dir = frontend / "public"
        backend_app = self.root / "app.py"

        required_files = (
            index_html, package_json, vite_config, main_tsx, app_tsx,
            index_css, api_ts, backend_app,
        )
        missing = [
            path.relative_to(self.root).as_posix()
            for path in required_files
            if not path.is_file()
        ]

        if missing:
            return {
                "checks": {"required_files": False},
                "missing_files": missing,
                "valid": False,
            }

        html = index_html.read_text(encoding="utf-8")
        package = json.loads(package_json.read_text(encoding="utf-8"))
        vite = vite_config.read_text(encoding="utf-8")
        main = main_tsx.read_text(encoding="utf-8")
        app = app_tsx.read_text(encoding="utf-8")
        css = index_css.read_text(encoding="utf-8")
        api = api_ts.read_text(encoding="utf-8")
        backend = backend_app.read_text(encoding="utf-8")

        deps = {}
        deps.update(package.get("dependencies", {}))
        deps.update(package.get("devDependencies", {}))
        scripts = package.get("scripts", {})

        component_names = (
            "ChatWindow.tsx",
            "Composer.tsx",
            "MessageBubble.tsx",
            "Sidebar.tsx",
            "SettingsPanel.tsx",
            "TopBar.tsx",
        )

        public_assets = (
            [path for path in public_dir.iterdir() if path.is_file()]
            if public_dir.is_dir()
            else []
        )

        checks = {
            "vite_entrypoint": (
                'id="root"' in html
                and '/src/main.tsx' in html
            ),
            "react_dependencies": (
                "react" in deps
                and "react-dom" in deps
                and "vite" in deps
                and "@vitejs/plugin-react" in deps
            ),
            "build_script": (
                "build" in scripts
                and "vite build" in str(scripts.get("build", ""))
            ),
            "main_mounts_app": (
                "createRoot" in main
                and "<App" in main
                and "./index.css" in main
            ),
            "app_source_present": (
                "function App" in app
                or "default function App" in app
                or "export default" in app
            ),
            "api_health_route": "/api/health" in api,
            "api_chat_route": "/api/chat/stream" in api,
            "backend_health_route": "/api/health" in backend,
            "backend_chat_route": "/api/chat/stream" in backend,
            "vite_api_proxy": (
                "'/api'" in vite
                and "127.0.0.1:8000" in vite
            ),
            "tailwind_entry_css": (
                "@tailwind base" in css
                and "@tailwind components" in css
                and "@tailwind utilities" in css
            ),
            "components_present": all(
                (components_dir / name).is_file()
                for name in component_names
            ),
            "public_assets_present": len(public_assets) >= 2,
            "no_html_cdn": not self._html_has_remote_reference(html),
            "no_css_remote_assets": not self._css_has_remote_asset(css),
        }

        return {
            "checks": checks,
            "missing_files": [],
            "valid": all(checks.values()),
        }

    def validate_gateway_contract(self):
        source = (
            self.root
            / (
                "services/api_gateway/"
                "routes.py"
            )
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
            for route
            in required_routes
            if route not in source
        ]

        return {
            "required_route_count": len(
                required_routes
            ),
            "missing_routes": (
                missing
            ),
            "valid": (
                not missing
            ),
        }

    def validate_all(self):
        structure = (
            self.validate_structure()
        )

        coverage = (
            self
            .validate_folder_test_coverage()
        )

        imports = (
            self.validate_python_imports()
        )

        frontend = (
            self.validate_frontend_contract()
        )

        gateway = (
            self.validate_gateway_contract()
        )

        return {
            "structure": structure,
            "folder_test_coverage": (
                coverage
            ),
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
