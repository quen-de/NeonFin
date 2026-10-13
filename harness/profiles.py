"""Device profiles and the routes the harness captures."""

from __future__ import annotations

from dataclasses import dataclass

# Jellyfin picks layout-mobile from the user agent, not the viewport.
ANDROID_UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36"


@dataclass(frozen=True)
class Profile:
    name: str
    context: dict
    cpu_throttle: int


PROFILES = {
    "desktop": Profile("desktop", {"viewport": {"width": 1440, "height": 900}}, 1),
    "phone": Profile(
        "phone",
        {
            "viewport": {"width": 412, "height": 915},
            "device_scale_factor": 2,
            "is_mobile": True,
            "has_touch": True,
            "user_agent": ANDROID_UA,
        },
        4,
    ),
}


@dataclass(frozen=True)
class Route:
    name: str
    path: str  # hash route, formatted with config items and search_term
    anchor: str  # must be visible for the capture to count
    ready: str | None = None  # visible before the state action runs
    state: str | None = None
    logged_in: bool = True
    needs: frozenset[str] = frozenset()  # plugins without which the route does not exist


DETAIL = ".detailPagePrimaryContainer"
ROUTES = (
    Route("login", "#/login", "#txtManualName, .btnManual", logged_in=False),
    Route("home", "#/home", ".homeSectionsContainer"),
    Route("movies", "#/movies?topParentId={movies_library}", ".itemsContainer .card"),
    Route("series", "#/tv?topParentId={series_library}", ".itemsContainer .card"),
    Route("movie", "#/details?id={movie}", DETAIL),
    Route("show", "#/details?id={series}", DETAIL),
    Route("season", "#/details?id={season}", DETAIL),
    Route("episode", "#/details?id={playable}", DETAIL),
    Route("search", "#/search?query={search_term}", "#searchPage .card"),
    # A query nothing matches: the empty-results line.
    Route("noresults", "#/search?query=zzqxjvw", "#searchPage .noItemsMessage"),
    Route("prefs", "#/mypreferencesmenu", ".listItem"),
    # 12.1's preference pages render nothing without ?userId=.
    Route("display", "#/mypreferencesdisplay?userId={user_id}", ".MuiFilledInput-root"),
    Route("playback", "#/mypreferencesplayback?userId={user_id}", ".emby-select"),
    Route("subtitles", "#/mypreferencessubtitles?userId={user_id}", "#selectSubtitleLanguage"),
    Route("homeprefs", "#/mypreferenceshome?userId={user_id}", "#selectHomeSection1"),
    # The password fields are only waited on, never typed into.
    Route("profile", "#/userprofile?userId={user_id}", "#fldCurrentPassword"),
    Route("quickconnect", "#/quickconnect", "#txtQuickConnectCode"),
    # Hidden SyncPlay/remote menus also carry .MuiMenu-paper; anchor on the user menu itself.
    Route("usermenu", "#/home", "#app-user-menu .MuiMenu-paper", ready=".homeSectionsContainer", state="usermenu"),
    # The first select on Display is the language one; MUI mounts its menu as #menu-language.
    Route(
        "select", "#/mypreferencesdisplay?userId={user_id}", "#menu-language .MuiPaper-root", ready=".MuiFilledInput-root", state="select"
    ),
    # The detail page's "more" button opens the same .actionSheet on both
    # profiles; phone cards have no menu button and ignore long-press here.
    Route("actionsheet", "#/details?id={movie}", ".actionSheet", ready=DETAIL, state="actionsheet"),
    # More, then Add to playlist: a form dialog. Nothing is submitted.
    Route("dialog", "#/details?id={movie}", ".formDialog", ready=DETAIL, state="dialog"),
    # The sign-in page's user picker, with two made-up users (states.picker).
    Route("picker", "#/login", "#divUsers .card", ready="#txtManualName, .btnManual", state="picker", logged_in=False),
    Route("tooltip", "#/home", ".MuiTooltip-tooltip", ready=".homeSectionsContainer", state="tooltip"),
    Route("osd", "#/details?id={playable}", ".videoOsdBottom", ready=DETAIL, state="osd"),
    # Jellyfin Enhanced's own surfaces: its calendar page, which Plugin Pages hosts, and its
    # settings panel.
    Route(
        "calendar",
        "#/userpluginsettings.html?pageUrl=/JellyfinEnhanced/calendarPage",
        ".je-calendar-view-btn.active",
        needs=frozenset({"jellyfin-enhanced", "plugin-pages"}),
    ),
    Route(
        "jepanel", "#/home", "#jellyfin-enhanced-panel", ready=".homeSectionsContainer", state="jepanel",
        needs=frozenset({"jellyfin-enhanced"}),
    ),
)
PERF_ROUTES = ("home", "movies", "series", "movie")
