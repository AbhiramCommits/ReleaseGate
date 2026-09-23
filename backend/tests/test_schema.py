from pathlib import Path

from app.graphql import schema


def test_committed_sdl_matches_live_schema() -> None:
    committed = (Path(__file__).resolve().parent.parent / "schema.graphql").read_text()
    assert schema.as_str() == committed.rstrip("\n")
