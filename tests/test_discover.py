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


def film(id, container="mp4", vcodec="h264", vrange="SDR", acodec="aac", height=1080, *, vrange_type=None):
    return {
        "Id": id,
        "MediaSources": [
            {
                "Container": container,
                "MediaStreams": [
                    {
                        "Type": "Video",
                        "Codec": vcodec,
                        "VideoRange": vrange,
                        "Height": height,
                        "VideoRangeType": vrange_type or ("HDR10" if vrange == "HDR" else "SDR"),
                    },
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


def test_dolby_vision_alone_is_not_the_hdr_film():
    # A browser asked about Dolby Vision alone is asked a different question from HDR10 or HLG.
    films = [film("dv", "mkv", "hevc", "HDR", vrange_type="DOVI"), film("dvhdr", "mkv", "hevc", "HDR", vrange_type="DOVIWithHDR10")]
    assert discover.pick_player_titles(films) == {"play_hdr": "dvhdr"}


def test_dolby_vision_over_hdr10_plus_is_an_hdr_film():
    films = [film("dv", "mkv", "hevc", "HDR", vrange_type="DOVI"), film("dvplus", "mkv", "hevc", "HDR", vrange_type="DOVIWithHDR10Plus")]
    assert discover.pick_player_titles(films) == {"play_hdr": "dvplus"}
