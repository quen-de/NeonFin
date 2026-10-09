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
