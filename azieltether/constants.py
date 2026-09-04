"""Identity and protocol constants. Author is Aziel Eliab only."""

from __future__ import annotations

PRODUCT = "azieltether"
VERSION = "0.1.0"
AUTHOR = "Aziel Eliab"
LICENSE = "Apache-2.0"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 19740
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

USER_AGENT = "Mozilla/5.0"
GENESIS_PREV_HASH = "0" * 64

GITHUB = "https://github.com/AzielEliab/azieltether"
CATALOG = "https://aziel-runtime.vibelock.workers.dev/"
TETHER_BOOTSTRAP = "https://azieltether-download-tracker.vibelock.workers.dev"
DOWNLOAD = f"{TETHER_BOOTSTRAP}/download"

# Public HTTPS boards stay mesh-free. Health-check only — never write mesh here.
PUBLIC_SITES = {
    "godlock": "https://godlock.uk",
    "aziel-corpus": "https://www.azielcorpuslibrary.net",
    "aziel-runtime": "https://aziel-runtime.vibelock.workers.dev",
}

WORK_SCOPES = ("godlock", "aziel-corpus", "aziel-runtime")
LATTICE_SCOPE = "lattice"
PRECEDENT_SCOPE = "precedent"
SCOPES = (*WORK_SCOPES, LATTICE_SCOPE, PRECEDENT_SCOPE)
SCOPE_KINDS = {
    "godlock": ("receipt",),
    "aziel-corpus": ("ingest_envelope",),
    "aziel-runtime": ("catalog_event",),
    LATTICE_SCOPE: ("anchor",),
    PRECEDENT_SCOPE: ("conflict_receipt",),
}

# Products that may post lattice anchors. New slugs may join if they match PRODUCT_SLUG_RE.
LATTICE_PRODUCTS = frozenset(
    {
        "godlock",
        "aziel-corpus",
        "aziel-runtime",
        "azieltether",
        "foldlock",
        "az-clce",
        "temporallock",
        "staticclock",
        "miragegrid",
        "azos",
        "azai",
        "ark",
        "decisiongate",
        "forgereceipts",
        "veillock",
        "vibelock",
        "codelock",
        "shadowlock",
        "spectrallock",
        "chronolock",
        "postking",
        "glossafilter",
        "employeelock",
        "whistlelock",
        "trajectorylock",
        "zsolver",
        "azbot",
    }
)
PRODUCT_SLUG_RE = r"^[a-z][a-z0-9-]{1,40}$"

# Peer path must never write Aziel Library operator records.
FORBIDDEN_CORPUS_KINDS = frozenset(
    {
        "library_operator",
        "operator_record",
        "aziel_library_write",
        "operator_write",
    }
)

HOME_ENV = "AZIELTETHER_HOME"
BOOTSTRAP_ENV = "AZIELTETHER_BOOTSTRAP"
GODLOCK_INGEST_ENV = "AZIELTETHER_GODLOCK_INGEST"
CORPUS_INGEST_ENV = "AZIELTETHER_CORPUS_INGEST"
RUNTIME_INGEST_ENV = "AZIELTETHER_RUNTIME_INGEST"

MOTTO = "Prefer central. Fall back to peers. Reconcile when central returns."
ROLE = "central × decentral content/work tether"
NOTE_NOT_VPN = (
    "This is a content/work tether, not a VPN or anonymity network. "
    "Live public HTTPS boards stay mesh-free."
)
NOTE_NOT_MESH_WORKER = (
    "The download-tracker Worker is a bootstrap directory and holding pen, "
    "not a full mesh."
)
NOTE_CORPUS = (
    "aziel-corpus scope carries public Corpus ingest envelopes only. "
    "It never writes Aziel Library operator records."
)
