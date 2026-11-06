"""diary-install-viewer: Copy the static web viewer into a directory."""

import shutil
from importlib.resources import as_file, files
from pathlib import Path

import click

VIEWER_FILES = ("diary-viewer.html", "md-viewer-common.js")


@click.command()
@click.option("--page", default="diary-viewer.html", help="File name for the viewer page, e.g. index.html")
@click.argument("directory", type=click.Path(file_okay=False, path_type=Path))
def main(page, directory):
    """Copy the web viewer into DIRECTORY, next to which diary.json and aliases.json go.

    The viewer is a static page: put the output of `diary-digest export-web-json`
    beside it as diary.json, and optionally an aliases.json for the search.
    Existing viewer files are overwritten.
    """
    # The page loads the other files from its own directory, under their own names
    if Path(page).name != page or page in (".", "..", *VIEWER_FILES[1:]):
        raise click.BadParameter(
            f"must be a plain file name other than {', '.join(VIEWER_FILES[1:])}", param_hint="--page"
        )
    directory.mkdir(parents=True, exist_ok=True)
    for name in VIEWER_FILES:
        target = directory / (page if name == "diary-viewer.html" else name)
        with as_file(files("diary_md.viewer").joinpath(name)) as source:
            shutil.copyfile(source, target)
        click.echo(f"wrote {target}")


if __name__ == "__main__":
    main()
