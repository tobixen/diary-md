"""diary-install-viewer copies the packaged web viewer into a directory."""

from importlib.resources import files

from click.testing import CliRunner

from diary_md.cli.viewer import VIEWER_FILES, main


def test_viewer_files_are_package_data():
    for name in VIEWER_FILES:
        assert files("diary_md.viewer").joinpath(name).is_file(), name


def test_copies_the_viewer(tmp_path):
    result = CliRunner().invoke(main, [str(tmp_path / "site")])
    assert result.exit_code == 0, result.output
    for name in VIEWER_FILES:
        assert (tmp_path / "site" / name).read_bytes() == files("diary_md.viewer").joinpath(name).read_bytes()


def test_the_page_can_be_named(tmp_path):
    result = CliRunner().invoke(main, ["--page", "index.html", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "index.html").read_text().startswith("<!DOCTYPE html>")
    assert not (tmp_path / "diary-viewer.html").exists()
    assert (tmp_path / "md-viewer-common.js").is_file()


def test_a_page_name_that_would_break_the_site_is_refused(tmp_path):
    for page in ["md-viewer-common.js", "sub/x.html", "../x.html", ".."]:
        result = CliRunner().invoke(main, ["--page", page, str(tmp_path / "site")])
        assert result.exit_code == 2, (page, result.output)
        assert not (tmp_path / "x.html").exists()
