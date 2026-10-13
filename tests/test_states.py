import pytest
from playwright.sync_api import sync_playwright

from harness import session, states
from harness.profiles import PROFILES


@pytest.fixture
def page():
    with sync_playwright() as pw:
        b = session.launch(pw)
        ctx, p = session.new_page(b, PROFILES["desktop"], None, None)
        yield p
        b.close()


def test_an_api_path_matches_whatever_the_case():
    match = states.api_path("/users/public")
    assert match("http://host:8096/Users/Public")
    assert match("http://host:8096/users/public?x=1")
    assert not match("http://host:8096/Users/Me")


def test_the_enhanced_panel_stays_open_once_the_state_has_opened_it(page):
    # Jellyfin Enhanced closes its panel 20 s after it opens, unless the pointer is inside it;
    # pages are shared between tests, so the state keeps it open.
    page.set_content("""<body><script>
      document.addEventListener('keydown', (e) => {
        if (e.key !== '?') return;
        const p = document.createElement('div');
        p.id = 'jellyfin-enhanced-panel';
        p.textContent = 'panel';
        let inside = false;
        p.addEventListener('mouseenter', () => { inside = true; });
        setTimeout(() => { if (!inside) p.remove(); }, 200);
        document.body.append(p);
      });
    </script></body>""")
    states.jepanel(page)
    page.wait_for_timeout(400)
    assert page.locator("#jellyfin-enhanced-panel").count() == 1
