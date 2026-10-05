from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "frontend" / "src" / "components"

REQUIRED = (
    "ChatWindow.tsx",
    "Composer.tsx",
    "MessageBubble.tsx",
    "Sidebar.tsx",
    "SettingsPanel.tsx",
    "TopBar.tsx",
)


def main():
    missing = [name for name in REQUIRED if not (COMPONENTS / name).is_file()]
    if missing:
        raise AssertionError("Missing React components: " + ", ".join(missing))

    print("FRONTEND COMPONENTS TEST: PASS")


if __name__ == "__main__":
    main()
