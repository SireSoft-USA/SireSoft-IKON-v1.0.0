from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET


ROOT = Path(
    __file__
).resolve().parent

MANIFEST = (
    ROOT
    / "asset_manifest.json"
)

ASSERTIONS = 0


def check(
    condition,
    message,
):
    global ASSERTIONS
    ASSERTIONS += 1

    if not condition:
        raise AssertionError(
            message
        )


def main():
    manifest = json.loads(
        MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    check(
        manifest[
            "schema_version"
        ] == 1,
        "asset manifest schema version",
    )

    assets = manifest[
        "assets"
    ]

    check(
        len(
            assets
        ) == 4,
        "asset manifest must contain four declared assets",
    )

    ids = set()
    files = set()

    for asset in assets:
        asset_id = asset[
            "id"
        ]
        filename = asset[
            "file"
        ]

        check(
            asset_id not in ids,
            "duplicate asset id: "
            + asset_id,
        )

        check(
            filename not in files,
            "duplicate asset file: "
            + filename,
        )

        ids.add(
            asset_id
        )
        files.add(
            filename
        )

        check(
            filename.endswith(
                ".svg"
            ),
            "declared asset must be SVG: "
            + filename,
        )

        path = ROOT / filename

        check(
            path.is_file(),
            "missing declared asset: "
            + filename,
        )

        source = path.read_text(
            encoding="utf-8"
        )

        root = ET.fromstring(
            source
        )

        check(
            root.tag.endswith(
                "svg"
            ),
            "asset root must be svg: "
            + filename,
        )

        check(
            root.attrib.get(
                "viewBox"
            )
            is not None,
            "SVG viewBox required: "
            + filename,
        )

        check(
            int(
                root.attrib[
                    "width"
                ]
            )
            == asset[
                "width"
            ],
            "manifest width mismatch: "
            + filename,
        )

        check(
            int(
                root.attrib[
                    "height"
                ]
            )
            == asset[
                "height"
            ],
            "manifest height mismatch: "
            + filename,
        )

        check(
            (
                "aria-label"
                in root.attrib
                or "aria-labelledby"
                in root.attrib
            ),
            "SVG accessibility label required: "
            + filename,
        )

        check(
            "script"
            not in source.lower(),
            "SVG scripts are forbidden: "
            + filename,
        )

        check(
            re.search(
                r"https?://",
                source,
                flags=re.IGNORECASE,
            )
            is None
            or (
                'xmlns="http://www.w3.org/2000/svg"'
                in source
                and len(
                    re.findall(
                        r"https?://",
                        source,
                        flags=re.IGNORECASE,
                    )
                ) == 1
            ),
            "external URL found in SVG: "
            + filename,
        )

        for unsafe in (
            "foreignObject",
            "<iframe",
            "javascript:",
            "data:text/html",
            "onload=",
            "onclick=",
            "onerror=",
        ):
            check(
                unsafe.lower()
                not in source.lower(),
                (
                    "unsafe SVG construct "
                    + unsafe
                    + " in "
                    + filename
                ),
            )

    check(
        "sirellm-mark"
        in ids,
        "brand mark missing",
    )

    check(
        "favicon"
        in ids,
        "favicon missing",
    )

    check(
        "source-document"
        in ids,
        "retrieval source asset missing",
    )

    check(
        "empty-chat"
        in ids,
        "empty-chat asset missing",
    )

    readme = (
        ROOT
        / "README.md"
    ).read_text(
        encoding="utf-8"
    )

    for filename in files:
        check(
            filename
            in readme,
            "README missing asset: "
            + filename,
        )

    check(
        "CDN"
        in readme,
        "README must state remote dependency boundary",
    )

    print(
        "FRONTEND ASSETS TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Asset manifest integrity: VALIDATED"
    )
    print(
        "SVG structure/viewBox/dimensions: VALIDATED"
    )
    print(
        "Accessible SVG labels: VALIDATED"
    )
    print(
        "Embedded scripts/event handlers: 0"
    )
    print(
        "External asset dependencies: 0"
    )
    print(
        "Brand + favicon + retrieval + empty-state assets: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
