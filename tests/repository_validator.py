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
            self.root.rglob(
                "*.py"
            )
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
            for path
            in self.root.iterdir()
            if path.is_dir()
        }

        local_module_names = {
            path.stem
            for path
            in python_files
        }

        external = set()
        parse_errors = []

        for path in python_files:
            relative = (
                path.relative_to(
                    self.root
                )
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
                    "error": str(
                        error
                    ),
                })
                continue

            for node in ast.walk(
                tree
            ):
                if isinstance(
                    node,
                    ast.Import,
                ):
                    names = [
                        alias.name
                        for alias
                        in node.names
                    ]

                elif isinstance(
                    node,
                    ast.ImportFrom,
                ):
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
                    root_name = (
                        name.split(
                            "."
                        )[0]
                    )

                    if (
                        root_name
                        in stdlib
                        or root_name
                        in top_level_roots
                        or root_name
                        in local_module_names
                    ):
                        continue

                    external.add(
                        root_name
                    )

        return {
            "python_file_count": len(
                python_files
            ),
            "external_roots": sorted(
                external
            ),
            "parse_errors": (
                parse_errors
            ),
            "valid": (
                not external
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
                / (
                    "frontend/assets/"
                    "asset_manifest.json"
                )
            ).read_text(
                encoding="utf-8"
            )
        )

        checks = {
            "local_css": (
                "./css/app.css"
                in html
            ),
            "local_js": (
                "./js/app.js"
                in html
            ),
            "health_route": (
                '"/v1/health"'
                in js
            ),
            "chat_route": (
                '"/v1/chat"'
                in js
            ),
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
                not self
                ._html_has_remote_reference(
                    html
                )
            ),
            "no_css_remote_assets": (
                not self
                ._css_has_remote_asset(
                    css
                )
            ),
        }

        return {
            "checks": checks,
            "valid": all(
                checks.values()
            ),
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
