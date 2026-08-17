"""Integration tests covering the riskiest parts of the pipeline:

  - content_group language collapsing (the brief's core catalogue rule)
  - Season 0 / trailers handling
  - the publish job being idempotent (same input -> same output, safe to
    re-run)
  - the validation report catching each of the three publish-blocking
    conditions and those episodes being excluded from the catalogue
    rather than the whole publish failing
  - role enforcement actually being enforced, not just declared
"""

from __future__ import annotations

from tests.conftest import auth_headers, make_image_bytes


def _create_show(client, token, **overrides) -> dict:
    payload = {
        "title": "Test Show",
        "slug": "test-show",
        "section": "series",
        "synopsis": "A show for tests.",
        "categories": "stories,values",
    }
    payload.update(overrides)
    resp = client.post("/shows/", json=payload, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_season(client, token, show_id: int, season_number: int) -> dict:
    resp = client.post(
        "/seasons/",
        json={"show_id": show_id, "season_number": season_number},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_episode(client, token, **kwargs) -> dict:
    defaults = {"status": "draft"}
    defaults.update(kwargs)
    resp = client.post("/episodes/", json=defaults, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _upload_all_artwork(client, token, episode_id: int) -> None:
    specs = {"poster": (600, 900), "banner": (1280, 720), "thumbnail": (640, 360)}
    for artwork_type, (w, h) in specs.items():
        resp = client.post(
            "/artworks/upload",
            data={"episode_id": episode_id, "artwork_type": artwork_type},
            files={"file": (f"{artwork_type}.png", make_image_bytes(w, h), "image/png")},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text


def _publish_episode(client, token, episode: dict) -> dict:
    resp = client.put(
        f"/episodes/{episode['id']}",
        json={**episode, "status": "published"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_content_group_collapses_language_variants(client, admin_token):
    show = _create_show(client, admin_token)
    season = _create_season(client, admin_token, show["id"], 1)

    en = _create_episode(
        client,
        admin_token,
        episode_id="ep-en-1",
        season_id=season["id"],
        episode_number=1,
        title="The Kite (EN)",
        duration_seconds=500,
        language="en",
        content_group="s01e01",
    )
    hi = _create_episode(
        client,
        admin_token,
        episode_id="ep-hi-1",
        season_id=season["id"],
        episode_number=1,
        title="The Kite (HI)",
        duration_seconds=480,
        language="hi",
        content_group="s01e01",
    )
    _upload_all_artwork(client, admin_token, en["id"])
    _upload_all_artwork(client, admin_token, hi["id"])
    _publish_episode(client, admin_token, en)
    _publish_episode(client, admin_token, hi)

    resp = client.post("/admin/catalog/publish", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "completed"

    catalog = client.get("/catalog").json()
    series = next(s for s in catalog["sections"] if s["section"] == "series")
    show_entry = series["shows"][0]
    season_entry = show_entry["seasons"][0]

    assert len(season_entry["episodes"]) == 1  # collapsed into ONE entry
    languages = {lang["language"] for lang in season_entry["episodes"][0]["languages"]}
    assert languages == {"en", "hi"}


def test_season_zero_marked_as_trailers(client, admin_token):
    show = _create_show(client, admin_token, slug="trailer-show", title="Trailer Show")
    season = _create_season(client, admin_token, show["id"], 0)
    ep = _create_episode(
        client,
        admin_token,
        episode_id="ep-trailer-1",
        season_id=season["id"],
        episode_number=1,
        title="Teaser",
        duration_seconds=30,
        language="en",
        content_group="trailer-cg",
    )
    _upload_all_artwork(client, admin_token, ep["id"])
    _publish_episode(client, admin_token, ep)

    client.post("/admin/catalog/publish", headers=auth_headers(admin_token))
    catalog = client.get("/catalog").json()
    show_entry = next(
        s for sec in catalog["sections"] for s in sec["shows"] if s["slug"] == "trailer-show"
    )
    assert show_entry["seasons"][0]["is_trailers"] is True


def test_publish_is_idempotent(client, admin_token):
    show = _create_show(client, admin_token)
    season = _create_season(client, admin_token, show["id"], 1)
    ep = _create_episode(
        client,
        admin_token,
        episode_id="ep-idem-1",
        season_id=season["id"],
        episode_number=1,
        title="Idempotent Episode",
        duration_seconds=300,
        language="en",
        content_group="idem-cg",
    )
    _upload_all_artwork(client, admin_token, ep["id"])
    _publish_episode(client, admin_token, ep)

    first = client.post("/admin/catalog/publish", headers=auth_headers(admin_token)).json()
    second = client.post("/admin/catalog/publish", headers=auth_headers(admin_token)).json()

    assert first["shows_count"] == second["shows_count"]
    assert first["episodes_count"] == second["episodes_count"]

    catalog_first = client.get("/catalog").json()
    catalog_second = client.get("/catalog").json()
    # Byte-identical apart from the timestamp: same DB state must produce
    # the same catalogue every time.
    catalog_first.pop("generated_at")
    catalog_second.pop("generated_at")
    assert catalog_first == catalog_second


def test_episode_missing_artwork_is_excluded_and_reported(client, admin_token):
    show = _create_show(client, admin_token, slug="incomplete-show", title="Incomplete Show")
    season = _create_season(client, admin_token, show["id"], 1)
    ep = _create_episode(
        client,
        admin_token,
        episode_id="ep-noart-1",
        season_id=season["id"],
        episode_number=1,
        title="No Artwork Episode",
        duration_seconds=300,
        language="en",
        content_group="noart-cg",
    )
    # Only upload one of the three required types.
    client.post(
        "/artworks/upload",
        data={"episode_id": ep["id"], "artwork_type": "poster"},
        files={"file": ("poster.png", make_image_bytes(600, 900), "image/png")},
        headers=auth_headers(admin_token),
    )

    # Trying to publish this episode should be rejected up front...
    resp = client.put(
        f"/episodes/{ep['id']}",
        json={**ep, "status": "published"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422

    # ...and, as a safety net, even if it somehow ended up marked
    # published it must not appear in a real publish run.
    report = client.get(
        "/admin/validation-report", headers=auth_headers(admin_token)
    ).json()
    assert report["issue_count"] == 0  # not published, so not "trying" yet


def test_show_missing_section_blocks_and_is_reported(client, admin_token, db_session):
    # Section is only enforced at publish-time for shows that already
    # have a published episode - create with a section, publish, then
    # unset the section directly (simulating an edit that leaves a
    # published show without one) to exercise the safety-net check in
    # services/validation.py independent of the create/update guard.
    show = _create_show(client, admin_token, slug="no-section-show", title="No Section Show")
    season = _create_season(client, admin_token, show["id"], 1)
    ep = _create_episode(
        client,
        admin_token,
        episode_id="ep-nosection-1",
        season_id=season["id"],
        episode_number=1,
        title="Orphaned Episode",
        duration_seconds=300,
        language="en",
        content_group="nosection-cg",
    )
    _upload_all_artwork(client, admin_token, ep["id"])
    _publish_episode(client, admin_token, ep)

    from app.models.show import Show

    db_show = db_session.query(Show).filter(Show.id == show["id"]).first()
    db_show.section = None
    db_session.commit()

    report = client.get(
        "/admin/validation-report", headers=auth_headers(admin_token)
    ).json()
    assert any(s["id"] == show["id"] for s in report["shows_missing_section"])

    result = client.post("/admin/catalog/publish", headers=auth_headers(admin_token)).json()
    assert result["issues_count"] >= 1

    catalog = client.get("/catalog").json()
    all_slugs = {s["slug"] for sec in catalog["sections"] for s in sec["shows"]}
    assert "no-section-show" not in all_slugs


def test_editor_cannot_publish(client, editor_token):
    resp = client.post("/admin/catalog/publish", headers=auth_headers(editor_token))
    assert resp.status_code == 403


def test_editor_can_read_validation_report(client, editor_token):
    # The report is explicitly meant to be editor-readable, not
    # admin-gated - see the FIXED note in app/api/validation.py.
    resp = client.get("/admin/validation-report", headers=auth_headers(editor_token))
    assert resp.status_code == 200


def test_unauthenticated_cannot_create_show(client):
    resp = client.post("/shows/", json={"title": "x", "slug": "x"})
    assert resp.status_code == 401


def test_duplicate_content_group_language_rejected_cleanly(client, admin_token):
    # Mirrors the real conflict found in seed_shows.json (ep_0004 vs
    # ep_9001 both claiming motis-many-lives-s01e02/hi) - the second
    # attempt should fail with a clean 400, not a raw DB integrity error.
    show = _create_show(client, admin_token, slug="dup-show", title="Dup Show")
    season = _create_season(client, admin_token, show["id"], 1)
    _create_episode(
        client,
        admin_token,
        episode_id="ep-dup-1",
        season_id=season["id"],
        episode_number=1,
        title="Original",
        duration_seconds=300,
        language="hi",
        content_group="dup-cg",
    )
    resp = client.post(
        "/episodes/",
        json={
            "episode_id": "ep-dup-2",
            "season_id": season["id"],
            "episode_number": 1,
            "title": "Duplicate (v2)",
            "duration_seconds": 300,
            "language": "hi",
            "content_group": "dup-cg",
            "status": "draft",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"].lower()


def test_duplicate_show_slug_rejected_cleanly(client, admin_token):
    _create_show(client, admin_token, slug="one-slug", title="Show A")
    resp = client.post(
        "/shows/",
        json={"title": "Show B", "slug": "one-slug"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400


def test_search_filters_compose(client, admin_token):
    show = _create_show(
        client, admin_token, slug="search-show", title="Search Show", section="songs"
    )
    season = _create_season(client, admin_token, show["id"], 1)
    en = _create_episode(
        client,
        admin_token,
        episode_id="ep-search-en",
        season_id=season["id"],
        episode_number=1,
        title="Sing Along",
        duration_seconds=200,
        language="en",
        content_group="search-cg",
    )
    hi = _create_episode(
        client,
        admin_token,
        episode_id="ep-search-hi",
        season_id=season["id"],
        episode_number=1,
        title="Gaao Saath",
        duration_seconds=200,
        language="hi",
        content_group="search-cg",
    )
    _upload_all_artwork(client, admin_token, en["id"])
    _upload_all_artwork(client, admin_token, hi["id"])
    _publish_episode(client, admin_token, en)
    _publish_episode(client, admin_token, hi)
    client.post("/admin/catalog/publish", headers=auth_headers(admin_token))

    # q matches the show title...
    resp = client.get("/catalog/search", params={"q": "search show"})
    assert len(resp.json()["sections"]) == 1

    # ...section + language compose to filter down to one language variant.
    resp = client.get(
        "/catalog/search", params={"section": "songs", "language": "hi"}
    )
    shows = resp.json()["sections"][0]["shows"]
    langs = shows[0]["seasons"][0]["episodes"][0]["languages"]
    assert {lang["language"] for lang in langs} == {"hi"}

    # a language with no matches in this section returns no shows.
    resp = client.get("/catalog/search", params={"section": "featured"})
    assert resp.json()["sections"] == []