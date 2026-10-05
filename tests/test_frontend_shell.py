import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    index = (FRONTEND / "index.html").read_text(encoding="utf-8")
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
    vite = (FRONTEND / "vite.config.ts").read_text(encoding="utf-8")

    check('id="root"' in index, "React root element missing")
    check('/src/main.tsx' in index, "Vite main.tsx entrypoint missing")
    check("react" in package.get("dependencies", {}), "React dependency missing")
    check("vite" in package.get("dependencies", {}) or "vite" in package.get("devDependencies", {}), "Vite dependency missing")
    check("vite build" in package.get("scripts", {}).get("build", ""), "Vite build script missing")
    check("react()" in vite, "Vite React plugin missing")
    check("'/api'" in vite, "Vite /api proxy missing")

    print("FRONTEND SHELL TEST: PASS")


if __name__ == "__main__":
    main()
