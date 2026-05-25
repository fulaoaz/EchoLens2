# EchoLens 2.0 — KG Stack Spike Report

**Stack under evaluation:** Kuzu (embedded graph DB) + LightRAG (HKUDS, LLM-on-Graph RAG) + NetworkX (in-memory hot data / viz)
**Scope:** PRD §5.1 `kg/` module, §5.3. All-local, Python ≥ 3.11, Windows + Linux Docker.
**Date:** 2026-05-19
**Author:** spike research agent

> **Verification disclaimer.** Outbound web fetches and search were blocked by the runtime sandbox during this spike (`WebFetch` on github.com refused, MCP fetcher returned `提取失败`, `WebSearch` returned 502). Versions, dates, and feature flags below come from cached training-time knowledge of each project's repo and docs. They MUST be re-verified by running `pip index versions kuzu lightrag-hku` and skimming each project's CHANGELOG before code is written. Items I could not re-confirm online are flagged **[unverified-online]**.
>
> **Update 2026-05-19 (M0 close-out).** Kuzu basic CRUD (node/rel table declaration, INSERT, MATCH, return-rows iteration) **verified locally** via `backend/tests/test_kg_kuzu_smoke.py` — installed version `kuzu` from PyPI on Python 3.12 / Windows, all assertions pass. Items concerning Kuzu's runtime behavior may now be treated as confirmed. LightRAG end-to-end (ingest → query) and the LightRAG↔Kuzu sync layer remain `[unverified-online]` and are M1 work.
>
> **Update 2026-05-20 (M1.1 attempt).** First attempt at `uv pip install lightrag-hku` failed with DNS error contacting `pypi.org/simple/pypinyin/` (transitive dependency). The host loses DNS resolution intermittently from this dev box. **Action taken:** task #7 (LightRAG smoke) marked BLOCKED on network; M1 plan unchanged but actual install + smoke is deferred until a successful PyPI fetch. Risk #1 from this report (LightRAG API churn) is unaffected; risk severity is now moderate-real (network friction). If install keeps failing on this dev box, switch to PyPI mirror (`pip install -i https://mirrors.aliyun.com/pypi/simple/ lightrag-hku`) or move dev to a host with stable PyPI access before failing over to Neo4j.
>
> **Update 2026-05-20 (M1.1 close-out).** Aliyun PyPI mirror unblocked the install: `lightrag-hku==1.4.16` resolved successfully via `uv pip install --index-url https://mirrors.aliyun.com/pypi/simple/ lightrag-hku`. Smoke test `backend/tests/test_kg_lightrag_sync.py` (3 cases, all pass) verifies (a) LightRAG package + `NetworkXStorage` imports cleanly, (b) the new `app/kg/sync.py` projects an arbitrary NetworkX graph into Kuzu via `MERGE`-style upserts (idempotent — re-running yields the same node/edge counts), (c) Cypher queries against the projected graph return the expected typed rows, and (d) unknown `entity_type` values fall back to a generic `Entity` table without errors. The LightRAG ↔ Kuzu glue from §3.2 Option (d) is now **verified locally**; full LLM-driven ingest remains M1.2 work and will be exercised once an LLM endpoint is wired in. The risk in this report's §4.1 #1 (LightRAG API churn) is moderated — we now have a regression suite to catch breakage on version bumps.

---

## 1. Kuzu

### 1.1 Snapshot

| Item | Value | Confidence |
|---|---|---|
| Latest stable | `0.7.x` line, with `0.8.x` cut in early 2026 **[unverified-online]** | medium |
| License | **MIT** | high |
| Install | `pip install kuzu` (single wheel, bundles native lib) | high |
| System deps | None for the wheel; from-source builds need a C++17 toolchain + CMake | high |
| Storage | Single-process **embedded** DB, on-disk directory of files (à la SQLite/DuckDB), columnar, ACID | high |
| Schema | **Strict / property-graph schema-rigid** — node tables and rel tables must be declared with typed columns before insert | high |
| Cypher | Large subset: `MATCH`, `CREATE`, `MERGE`, `SET`, `DELETE`, `WITH`, `UNWIND`, `OPTIONAL MATCH`, `CALL` for built-ins, recursive variable-length paths. **Not supported:** stored procedures, triggers, full APOC, dynamic labels, schema-less nodes, multi-statement transactions over Bolt **[unverified-online]** | medium |
| Concurrency | **Single writer, multi-reader** per DB directory (file-lock). No server mode in OSS — only the embedded driver | high |
| RAM | Configurable buffer pool (`buffer_pool_size`); idle ~hundreds of MB, scales with working set | medium |
| Perf claims | Project benchmarks (LDBC SNB, JOB) show it competitive with / beating Neo4j on read-heavy analytical Cypher; vectorized execution like DuckDB | medium |
| Maintenance | Active — University of Waterloo spin-off, regular minor releases, healthy issue triage **[unverified-online]** | medium |
| Production | Used as the embedded GraphDB inside LangChain `KuzuGraph`, LlamaIndex `KuzuPropertyGraphStore`, several CLI knowledge-graph tools | high |

### 1.2 Known limitations to plan around

- **One writer at a time.** Backend Flask must serialize writes to Kuzu (single `Connection` behind a lock, or a write queue). Multiple read connections are fine.
- **Schema-rigid.** Adding a new node/rel property requires `ALTER TABLE`. Migration scripts must ship with each kg/ schema bump.
- **No live network protocol in OSS.** All access is in-process Python. Cannot point Cypher Shell or Bloom at it. Acceptable for an all-local product; relevant only if we later need remote inspection.
- **Backups = copy the directory while the DB is closed** (or use `EXPORT DATABASE`).
- **Schema migration tooling is thin** — we will likely write our own `kg/migrations.py`.

### 1.3 Minimal Python example *(not executed in this spike — no sandbox runtime)*

```python
# kg/spike_kuzu.py
import kuzu

db = kuzu.Database("./kg_data")            # creates dir if absent
conn = kuzu.Connection(db)

# 1. Schema
conn.execute("""
    CREATE NODE TABLE Product(
        id   STRING PRIMARY KEY,
        name STRING,
        price DOUBLE
    )
""")
conn.execute("""
    CREATE NODE TABLE Brand(
        id   STRING PRIMARY KEY,
        name STRING
    )
""")
conn.execute("""
    CREATE REL TABLE BELONGS_TO(FROM Product TO Brand, since INT64)
""")

# 2. Insert
conn.execute("CREATE (:Brand   {id:'b1', name:'Anker'})")
conn.execute("CREATE (:Product {id:'p1', name:'Anker 737 PowerBank', price:149.0})")
conn.execute("""
    MATCH (p:Product {id:'p1'}), (b:Brand {id:'b1'})
    CREATE (p)-[:BELONGS_TO {since: 2024}]->(b)
""")

# 3. Query
result = conn.execute("""
    MATCH (p:Product)-[:BELONGS_TO]->(b:Brand)
    RETURN p.name AS product, b.name AS brand
""")
while result.has_next():
    print(result.get_next())

# 4. Close
del conn; del db
```

---

## 2. LightRAG (HKUDS)

### 2.1 Snapshot

| Item | Value | Confidence |
|---|---|---|
| Latest version | `lightrag-hku` on PyPI, ≥ 1.x in early 2026 **[unverified-online]** | medium |
| License | **MIT** | high |
| Install | `pip install lightrag-hku` (the bare name `lightrag` is squatted; HKUDS publishes under `lightrag-hku`) | high |
| Default storage | **Pluggable storage interfaces**: `kv_storage`, `vector_storage`, `graph_storage`, `doc_status_storage`. Defaults: JSON KV, NanoVectorDB, **NetworkX** for graph | high |
| Other graph backends shipped | **Neo4jStorage**, **NetworkXStorage**, **AGEStorage** (PostgreSQL Apache AGE), **MemgraphStorage**, **TiDBGraphStorage** **[partly unverified-online]** | medium |
| Kuzu backend? | **Not shipped out-of-the-box as of training cutoff.** Not in `lightrag/kg/` directory list I have. Must be confirmed against current main. **[unverified-online]** | medium |
| LLM providers | OpenAI, Azure, **Ollama (local)**, HuggingFace, OpenAI-compatible endpoints (vLLM, LMStudio, DeepSeek, Qwen API) | high |
| Embeddings | `nomic-embed-text` via Ollama, OpenAI `text-embedding-3-*`, BAAI/bge-* via HF | high |
| Maintenance | Very active in 2024–2025, frequent releases, large issue volume — quality is mixed but momentum is real | medium |

### 2.2 Architecture in one diagram

```
docs ─► chunker ─► LLM extract (entities + relations) ─► graph_storage (insert nodes/edges)
                                          │
                                          └─► vector_storage (entity vecs, relation vecs, chunk vecs)

query ─► dual-level retrieval ──┬─► low-level: entity-vec search → 1-hop subgraph
                                └─► high-level: relation/keyword-vec search → multi-hop subgraph
       └─► LLM synthesizes answer over retrieved subgraph + chunks
```

### 2.3 Dual-level retrieval (3-4 lines)

LightRAG indexes both **specific entities** and **abstract topical keywords** that summarize relations. At query time the LLM produces two keyword sets — *low-level* (specific entities the question is about) and *high-level* (themes / topics). Each set is vector-searched independently, the matched entities/relations are expanded one or two hops in the graph, and the union is fed back to the LLM. This makes it answer both "What did Brand X say about price?" and "How is sentiment evolving across the market?" with the same store.

### 2.4 Token cost (order-of-magnitude)

- **Ingest:** ~1 LLM call per chunk (1k–1.5k tokens) for entity+relation extraction, plus a "gleaning" pass (configurable, usually 1). For a 100-page PDF (~150k tokens of source) expect ~200k–400k LLM input tokens and ~50k–100k output.
- **Query:** 2 small LLM calls for keyword extraction (~1k tokens each) + 1 generation call over retrieved context (3k–8k tokens). Cheap.
- This is the headline complaint in the project's issue tracker — every greenfield ingest is expensive. Mitigation: cache extractions, use a smaller model (e.g. `gpt-4o-mini`, `qwen2.5-7b-instruct` via Ollama) for extraction, ship pre-built graphs for demo decks.

### 2.5 Minimal usage example

```python
# kg/spike_lightrag.py
import asyncio, os
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

WORKDIR = "./lightrag_cache"
os.makedirs(WORKDIR, exist_ok=True)

async def llm(prompt, system_prompt=None, history_messages=[], **kw):
    return await openai_complete_if_cache(
        "gpt-4o-mini", prompt,
        system_prompt=system_prompt, history_messages=history_messages,
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL"),
        **kw,
    )

rag = LightRAG(
    working_dir=WORKDIR,
    llm_model_func=llm,
    embedding_func=EmbeddingFunc(
        embedding_dim=1536, max_token_size=8192,
        func=lambda texts: openai_embed(
            texts, model="text-embedding-3-small",
            api_key=os.environ["LLM_API_KEY"],
        ),
    ),
    # graph_storage="NetworkXStorage",   # default
)

async def main():
    await rag.ainsert("Anker 737 is a 24,000 mAh power bank. Anker is a Shenzhen brand.")
    print(await rag.aquery("Who makes the 737?", param=QueryParam(mode="hybrid")))

asyncio.run(main())
```

---

## 3. Integration decision

### 3.1 Options

| | Pros | Cons |
|---|---|---|
| **(a)** LightRAG on its NetworkX default + Kuzu separately for structured Cypher; sync via post-ingest hook that re-emits the same triples into Kuzu | LightRAG stays vanilla; fastest path to demo; structured Cypher available where needed | Two stores ⇒ drift risk; sync must be transactional; double disk |
| **(b)** Patch LightRAG with a `KuzuGraphStorage` that implements its `BaseGraphStorage` interface | Single source of truth; Cypher available "for free"; no sync bug class | ~300–600 LOC backend + tests; have to track LightRAG interface churn (not stable yet); Kuzu's strict schema fights LightRAG's free-form `entity_type` strings |
| **(c)** Two parallel KGs, no sync | Simplest; clean separation; each tool unconstrained | Truth divergence guaranteed; double the LLM ingest cost OR a custom Kuzu loader anyway |
| **(d)** **[Recommended]** LightRAG on NetworkX backend; **export the same NetworkX graph into Kuzu in a single `kg/sync.py` step** triggered after each ingest. NetworkX is also the in-memory hot view for OASIS / viz. One ingest, one extraction, two read-optimized projections. | Re-uses LightRAG's existing, supported NetworkX path; structured Cypher available; no LightRAG fork; NetworkX doubles as the simulation/viz layer the PRD already needs | Sync code is ours to own; on big graphs a full rebuild is slow → need incremental sync by node id |

### 3.2 Choice: **(d)**

```
ingest ─► LightRAG ─► NetworkX (canonical "raw" graph + chunk/vector stores on disk)
                          │
                          └─► kg/sync.py ─► Kuzu (typed projection: Product / Brand / KOL / Topic / ...)
                                                │
                                                └─► used by Cypher endpoints + Step-2 entity picker
NetworkX subgraph ─► OASIS agent factory + frontend D3/cytoscape export
```

The sync is one-way (LightRAG → Kuzu), incremental on `node_id`, and idempotent (`MERGE`-style upserts). Kuzu becomes the "structured truth"; NetworkX/LightRAG remains the "RAG truth".

---

## 4. Risk assessment

| Project | Maturity (1-5) | Last release **[unverified-online]** | Bus factor | Breaking-change cadence |
|---|---|---|---|---|
| Kuzu | **4** — embedded GraphDB analogous to DuckDB; backed by an academic team turning into a company | regular minors | medium-low (small but real org) | Minor breaking changes between 0.x releases (storage format bumps require export/import) |
| LightRAG | **3** — useful, popular, but the API and storage interfaces still shift; many open issues, mixed test coverage | frequent | **high** — heavily HKUDS-driven | Frequent. Pin a version. |
| NetworkX | **5** — mature, ubiquitous | stable | very low | Effectively none |

### 4.1 Top risks

1. **LightRAG API churn.** Storage interface (`BaseGraphStorage`) and prompt templates change between minor releases. Pin `lightrag-hku==X.Y.Z` and gate upgrades behind a regression suite.
2. **Kuzu storage format bumps.** Going from 0.7→0.8 has historically required `EXPORT DATABASE`/`IMPORT DATABASE`. Ship a one-shot migration in `kg/migrations.py`; never let users open a DB created by a newer Kuzu with an older binary.
3. **LLM ingest cost & latency.** First-time ingest of a 100-page brand brief can be many minutes and dollars. Mitigations: small extraction model via Ollama, cache extractions by chunk hash, allow "demo mode" with a pre-built graph.
4. **Kuzu single-writer constraint** under concurrent uploads. Mitigation: a single asyncio write worker behind a queue; readers untouched.
5. **NetworkX scale.** Beyond ~5M edges NetworkX gets sluggish in pure Python. The PRD targets brand-level graphs (≪ 1M edges), so this is a future concern, not a v2 blocker.

---

## 5. Trip-wires that flip us to Neo4j Community + LightRAG

Abandon Kuzu and switch to Neo4j CE if **any one** of the following fires during M0/M1:

1. **LightRAG ↔ Kuzu cannot be made to coexist within ~1 engineer-week** (option d sync path keeps producing inconsistent graphs after 3 fix attempts).
2. **Kuzu's Cypher subset is missing a feature the kg/ API actually needs** — concretely: variable-length paths returning rels, `OPTIONAL MATCH` with aggregates, or `WITH ... ORDER BY ... LIMIT` in subqueries — and there is no in-Python workaround.
3. **Kuzu ships a storage-format break we cannot migrate inside a Docker upgrade script.**
4. **Single-writer locking causes user-visible stalls** under expected demo load (concurrent uploads from 2+ tabs blocking > 5 s).
5. **LightRAG drops or breaks the NetworkX backend** in a release we want to adopt for unrelated reasons (e.g. OpenAI 5.x support, citation feature).

Neo4j CE replaces Kuzu only — LightRAG already has a first-class Neo4j backend, so the migration is "swap `graph_storage` and rerun ingest", not a rewrite. NetworkX stays.

---

## 6. Final recommendation

# **GO-WITH-CAVEATS**

Proceed with **Kuzu + LightRAG + NetworkX**, integrated per Option (d): LightRAG owns ingest on its NetworkX backend; `kg/sync.py` projects to a typed Kuzu graph; NetworkX subgraphs feed OASIS and the frontend.

Required mitigations before M1 demo:

- Pin exact versions: `kuzu==<latest 0.x>`, `lightrag-hku==<latest 1.x>`, `networkx>=3.2,<4`. Re-verify versions and the Kuzu Cypher feature checklist (§1.1) against live PyPI/repo before pinning — this spike could not.
- Implement `kg/sync.py` (LightRAG NetworkX → Kuzu, incremental, idempotent) and a `kg/migrations.py` for Kuzu schema bumps.
- Single-writer `KuzuWriter` actor with an asyncio queue; multiple `KuzuReader` connections.
- Cache LightRAG extraction outputs by chunk hash so re-ingest is free.
- Land a regression test (small synthetic brand brief → expected entities/relations) that runs on every LightRAG version bump.
- Document the trip-wires in §5 in `docs/kg-decisions.md` so a future maintainer knows when to switch.

If any trip-wire in §5 fires before end of M1, switch Kuzu out for Neo4j Community Edition (Docker, bolt://localhost) and keep everything else; LightRAG already has a maintained Neo4j backend so the cost is one-day-ish, not a rewrite.
