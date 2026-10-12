from harness import discover


def test_merge_local_takes_new_items_and_keeps_every_developer_key():
    old = {"items": {"movie": "old"}, "volatile": [".v"], "neutrality_terms": ["x"]}
    found = {"items": {"movie": "new"}, "search_term": "the", "volatile": [".d"]}
    assert discover.merge_local(old, found) == {
        "items": {"movie": "new"},
        "search_term": "the",
        "volatile": [".v"],
        "neutrality_terms": ["x"],
    }


def film(id, container="mp4", vcodec="h264", vrange="SDR", acodec="aac", height=1080):
    return {
        "Id": id,
        "MediaSources": [
            {
                "Container": container,
                "MediaStreams": [
                    {"Type": "Video", "Codec": vcodec, "VideoRange": vrange, "Height": height},
                    {"Type": "Audio", "Codec": acodec},
                ],
            }
        ],
    }


def test_player_titles_are_a_plain_h264_mp4_and_an_hevc_hdr_film():
    films = [
        film("small", height=528),
        film("ac3", acodec="ac3"),
        film("mkv", container="mkv"),
        film("direct"),
        film("hdr-eac3", "mkv", "hevc", "HDR", "eac3"),
        film("hdr", "mkv", "hevc", "HDR"),
    ]
    assert discover.pick_player_titles(films) == {"play_direct": "direct", "play_hdr": "hdr"}


def test_an_hdr_film_without_aac_sound_still_counts():
    assert discover.pick_player_titles([film("x", "mkv", "hevc", "HDR", "eac3")]) == {"play_hdr": "x"}


def test_a_container_list_naming_mp4_counts_as_mp4():
    assert discover.pick_player_titles([film("d", container="mov,mp4,m4a,3gp,3g2,mj2")]) == {"play_direct": "d"}
