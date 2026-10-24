import pytest
from PIL import Image

from harness import shots


@pytest.mark.parametrize("url", ["http://localhost:8096", "http://127.0.0.1:8097/", "http://[::1]:8096"])
def test_screenshots_come_from_this_machine(url):
    shots.require_local(url)


def test_screenshots_never_come_from_another_server():
    with pytest.raises(shots.ShotError, match="demo server only"):
        shots.require_local("http://192.0.2.10:8096")


def test_screenshots_come_from_the_demo_server_by_name():
    shots.require_demo_server({"ServerName": "Demo"})


@pytest.mark.parametrize("info", [{"ServerName": "My Jellyfin"}, {}])
def test_screenshots_never_come_from_another_local_server(info):
    # Another Jellyfin on this machine is local too: its name tells it from the demo.
    with pytest.raises(shots.ShotError, match="demo server only"):
        shots.require_demo_server(info)


def test_side_by_side_keeps_each_image_and_the_gap():
    a, b = Image.new("RGB", (10, 20), "red"), Image.new("RGB", (30, 10), "blue")
    out = shots.side_by_side([a, b], gap=4)
    assert out.size == (44, 20) and out.getpixel((0, 0)) == (255, 0, 0) and out.getpixel((14, 0)) == (0, 0, 255)


def test_grid_lays_four_images_in_two_rows():
    out = shots.grid([Image.new("RGB", (10, 10), c) for c in ("red", "green", "blue", "white")], cols=2, gap=2)
    assert out.size == (22, 22) and out.getpixel((21, 21)) == (255, 255, 255)


def test_webp_fits_the_width_and_the_size_limit(tmp_path):
    path = tmp_path / "x.webp"
    shots.webp(Image.linear_gradient("L").resize((1600, 1000)).convert("RGB"), path, 1440)
    assert path.stat().st_size <= shots.MAX_BYTES and Image.open(path).size == (1440, 900)


def test_webp_refuses_an_image_it_cannot_fit(tmp_path, monkeypatch):
    monkeypatch.setattr(shots, "MAX_BYTES", 100)
    with pytest.raises(shots.ShotError, match="stays over"):
        shots.webp(Image.effect_noise((400, 300), 64).convert("RGB"), tmp_path / "x.webp", 400)
