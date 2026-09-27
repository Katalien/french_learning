"""Новые идентификаторы (contracts/cli.md: new-ids)."""

import re
from pathlib import Path

from french_learning.agent.ids import existing_ids, new_ids


def test_new_ids_are_unique_and_well_formed(store: Path):
    ids = new_ids(store, "ex", 5)
    assert len(set(ids)) == 5
    assert all(re.fullmatch(r"ex-[a-z2-7]{8}", i) for i in ids)
    assert not set(ids) & existing_ids(store)


def test_existing_ids_include_staging(store: Path):
    staged = store / ".staging/op1/lessons/001/exercises"
    staged.mkdir(parents=True)
    (staged / "ex-stagedaa.yaml").write_text("id: ex-stagedaa\n", encoding="utf-8")
    ids = existing_ids(store)
    assert "ex-stagedaa" in ids
    assert "ex-gapchoic" in ids
    assert "top-articles" in ids


def test_collision_is_avoided(store: Path, monkeypatch):
    sequence = iter(["ex-gapchoic", "ex-freshaaa"])
    monkeypatch.setattr("french_learning.agent.ids.new_id", lambda prefix: next(sequence))
    assert new_ids(store, "ex", 1) == ["ex-freshaaa"]
