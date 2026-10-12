import pytest

from harness import plugins


def test_all_switches_nothing_off_and_none_switches_everything_off():
    assert plugins.parse_state("all") == frozenset()
    assert plugins.parse_state("none") == frozenset(plugins.PLUGINS)


def test_without_names_one_or_more_plugins():
    assert plugins.parse_state("without:media-bar,jellyfin-enhanced") == {"media-bar", "jellyfin-enhanced"}


@pytest.mark.parametrize("spec", ["some", "without:", "without:nope"])
def test_bad_states_are_rejected(spec):
    with pytest.raises(plugins.PluginStateError):
        plugins.parse_state(spec)


def test_blocks_matches_plugin_paths_even_under_a_base_path():
    off = frozenset({"media-bar"})
    assert plugins.blocks("https://jf.example/MediaBar/slideshowpure.js", off)
    assert plugins.blocks("https://jf.example/jellyfin/MediaBar/WebConfig?x=1", off)
    assert not plugins.blocks("https://jf.example/HomeScreen/Sections", off)
    assert not plugins.blocks("https://jf.example/web/?q=/MediaBar/", off)


def test_media_bar_and_media_bar_enhanced_switch_off_apart():
    enhanced = "https://jf.example/MediaBarEnhanced/Resources/mediaBarEnhanced.js"
    assert plugins.blocks(enhanced, frozenset({"media-bar-enhanced"}))
    assert not plugins.blocks(enhanced, frozenset({"media-bar"}))
    assert not plugins.blocks("https://jf.example/MediaBar/slideshowpure.js", frozenset({"media-bar-enhanced"}))
