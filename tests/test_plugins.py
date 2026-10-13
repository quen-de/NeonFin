import pytest

from harness import plugins


def test_all_switches_nothing_off_and_none_switches_everything_off():
    assert plugins.parse_state("all") == frozenset()
    assert plugins.parse_state("none") == frozenset(plugins.PLUGINS)


def test_without_names_one_or_more_plugins():
    assert plugins.parse_state("without:media-bar-enhanced,jellyfin-enhanced") == {"media-bar-enhanced", "jellyfin-enhanced"}


@pytest.mark.parametrize("spec", ["some", "without:", "without:nope"])
def test_bad_states_are_rejected(spec):
    with pytest.raises(plugins.PluginStateError):
        plugins.parse_state(spec)


def test_blocks_matches_plugin_paths_even_under_a_base_path():
    off = frozenset({"media-bar-enhanced"})
    assert plugins.blocks("https://jf.example/MediaBarEnhanced/Resources/mediaBarEnhanced.js", off)
    assert plugins.blocks("https://jf.example/jellyfin/MediaBarEnhanced/WebConfig?x=1", off)
    assert not plugins.blocks("https://jf.example/HomeScreen/Sections", off)
    assert not plugins.blocks("https://jf.example/web/?q=/MediaBarEnhanced/", off)


def test_the_old_media_bar_is_no_longer_supported():
    with pytest.raises(plugins.PluginStateError):
        plugins.parse_state("without:media-bar")


def test_routes_only_need_plugins_the_harness_can_switch_off():
    from harness.profiles import ROUTES

    assert all(r.needs <= plugins.PLUGINS.keys() for r in ROUTES)
    assert {r.name for r in ROUTES if r.needs} == {"calendar", "jepanel"}
