from harness import states


def test_an_api_path_matches_whatever_the_case():
    match = states.api_path("/users/public")
    assert match("http://host:8096/Users/Public")
    assert match("http://host:8096/users/public?x=1")
    assert not match("http://host:8096/Users/Me")
