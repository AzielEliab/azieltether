"""Cross-product survival lattice: any surviving tip rehydrates the others."""

from __future__ import annotations

from azieltether.lattice import mint_anchor, mint_survival_round, rehydrate, verify_lattice
from azieltether.store import Store


def test_godlock_and_corpus_mutual_survival(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    god = store.mint_batch("godlock", "receipt", {"note": "board work"})
    corpus = store.mint_batch("aziel-corpus", "ingest_envelope", {"title": "public page"})
    posted = mint_survival_round(store)
    assert len(posted) == 2
    assert verify_lattice(store.load_batches("lattice"))["ok"] is True

    from_fold = rehydrate(store.load_batches("lattice"), surviving_product="godlock", surviving_tip=god["hash"])
    assert from_fold["ok"] is True
    assert from_fold["aziel-corpus"] == corpus["hash"]
    assert from_fold["godlock"] == god["hash"]

    from_corpus = rehydrate(store.load_batches("lattice"), surviving_product="aziel-corpus")
    assert from_corpus["godlock"] == god["hash"]


def test_any_product_anchor_rehydrates_godlock_and_corpus(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    god = store.mint_batch("godlock", "receipt", {"note": "g"})
    corpus = store.mint_batch("aziel-corpus", "ingest_envelope", {"title": "c"})
    fold_tip = "a" * 64
    mint_anchor(store, "godlock")
    mint_anchor(store, "aziel-corpus")
    # FoldLock (or any sibling) posts an anchor carrying the same cross-links.
    mint_anchor(store, "foldlock", tip_hash=fold_tip)
    recovered = rehydrate(store.load_batches("lattice"), surviving_product="foldlock", surviving_tip=fold_tip)
    assert recovered["ok"] is True
    assert recovered["godlock"] == god["hash"]
    assert recovered["aziel-corpus"] == corpus["hash"]
    assert recovered["rehydrated"]["foldlock"] == fold_tip


def test_broken_lattice_refused(tmp_path):
    store = Store(tmp_path)
    store.ensure_node()
    store.mint_batch("godlock", "receipt", {"note": "g"})
    mint_anchor(store, "godlock")
    anchors = store.load_batches("lattice")
    anchors[0]["payload"] = {**anchors[0]["payload"], "tip_hash": "b" * 64}
    assert verify_lattice(anchors)["ok"] is False
