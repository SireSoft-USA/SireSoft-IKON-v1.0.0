from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "src"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    main_source = (SRC / "main.tsx").read_text(encoding="utf-8")
    app_source = (SRC / "App.tsx").read_text(encoding="utf-8")
    css = (SRC / "index.css").read_text(encoding="utf-8")

    check("createRoot" in main_source, "React root mounting missing")
    check("<App" in main_source, "App is not mounted")
    check("./index.css" in main_source, "index.css is not imported")
    check("export default" in app_source, "App default export missing")
    check("@tailwind base" in css, "Tailwind base directive missing")
    check("@tailwind components" in css, "Tailwind components directive missing")
    check("@tailwind utilities" in css, "Tailwind utilities directive missing")

    print("FRONTEND SOURCE TEST: PASS")


if __name__ == "__main__":
    main()
