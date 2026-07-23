# Concepts

Technical reference for Labinat. Covers all core terms, how the system is structured, and how the pieces work together.

---

## Glossary

| Term | Definition |
|------|------------|
| **Catalog** | The registry of factories and frames. Path configured in `config.yaml` (default: `catalog/`). |
| **Factory** | A versioned stack profile: optional pipelines, frame definitions, maps, and a config schema. |
| **Frame** | A component-type definition: what fields a block may contain and what output files it produces. |
| **Block** | One instance of a frame — a validated JSON object describing a single component (e.g. one table, one screen). |
| **Concrete** | A named output file that a frame can generate. Each concrete maps to a template under `concretes/`. |
| **Bindings** | Snippet templates that describe how this frame's data appears when embedded inside another frame's output. |
| **Map** | A named key→value lookup registered as a custom schema type (`map.<name>`), typically shared across a factory. |
| **Workspace** | Where projects, blocks, and generated source live. Path configured in `config.yaml` (default: `workspace/`). |
| **Pipelines** | Optional factory shell command sequences (`init`, `build`, `run`, `debug`, `release`). Omit any a factory does not need. |

---

## How the pieces relate

```mermaid
flowchart LR
  subgraph catalog [Catalog]
    Factory[Factory\npipelines · maps · config]
    Frame[Frame\nschema · concretes · bindings]
    Factory --> Frame
  end
  subgraph workspace [Workspace]
    Project[Project]
    Block[Block JSON]
    Project --> Block
  end
  Frame --> Block
  Block --> Emit["Emit\nFrame.render + Jinja2"]
  Factory --> Pipelines["Pipelines\nPipelineExecuter"]
```

The **catalog** holds definitions; the **workspace** holds instances. A frame defines what a block may look like; a block is one concrete use of that frame inside a project.

---

## Persistence

All factory, frame, project, and block metadata is stored in a **SQLite database** (`data/database.db`, configured in `config.yaml`). The database schema is created automatically on first run.

On-disk directories under `catalog/factories/<name>/<version>/` hold files that do not live in a database column:

| On disk | Purpose |
|---------|---------|
| `base/` | Project scaffold templates (`DirectoryTemplate`) rendered by `Project.clone()` |
| `frames/<name>/module.py` | Optional Python module loaded with the frame |
| `frames/<name>/concretes/<name>.<ext>.j2` | Jinja2 output templates (or non-`.j2` static files) |
| `frames/<name>/bindings/<name>.j2` | Cross-frame snippet templates |

Runtime generated project trees live under `workspace/projects/<project_id>/` and are gitignored.

---

## Spec, Schema, and custom types

- Every resource wraps its JSON data in a [`Spec`](../base/Spec.py), which validates against a JSON Schema via [`Schema`](../base/Schema.py).
- Custom types register as `DataType` subclasses (`map.*`, `binding.*`). Schema `type` may be a single name or a list (OR semantics).
- `Spec.validate` always runs when a schema is provided — empty data still fails `required` fields.
- `Spec.decode` walks the data tree and applies registered type decoders (e.g. resolve `@block.users` bindings).

---

## Concretes

A **concrete** is one named output file a frame knows how to produce.

1. The frame's data lists concretes with `name`, `extension`, and `destination` (see `catalog/schemas/frame_schema.json`).
2. Template files live at `concretes/<name>.<extension>.j2` (or without `.j2` for static copy).
3. During emit, `Block.build` → `Frame.render` sets destinations from the concretes spec and writes rendered files under the project destination root.

---

## Bindings

**Bindings** describe cross-frame composition: how this frame's block data appears when referenced from another block (e.g. `@block.users`).

- Templates live at `bindings/<name>.j2`.
- At bind time, context keys are `src` (referenced block) and `dest` (referencing block). Top-level `self` is reserved by Jinja and must not be used.
- Decode returns a dict `{binding_name: rendered_text}` for the referenced frame's bindings.

---

## Maps

**Maps** are factory-level key/value dictionaries exposed as schema types `map.<name>`. Blocks inherit them via `Block.load` → `define_map`. Validation checks membership; decode substitutes the mapped value.

---

## Pipelines vs emit

| Concern | Driven by | Typical operations |
|---------|-----------|-------------------|
| Project toolchain | Factory `pipelines` → `PipelineExecuter` | `init`, `build`, `run`, `debug`, `release` (all optional) |
| Block → source file | Frame concretes + Jinja2 | emit via `Block.build` / `Frame.render` |

| Pipeline | Timing in `Project.build()` |
|----------|-----------------------------|
| *(scaffold)* | `clone()` — render factory `base/` into `src/<factory>/` |
| `init` | After clone, before emitting blocks (`cwd=src/<factory>`) |
| *(emit)* | Decode + render every registered block into its factory src tree |
| `build` | After emit (`cwd=src/<factory>`) |
| `run` / `debug` / `release` | On demand via `Project.run/debug/release` (same cwd) |

`Project.build()` order: **validate_config → clone → init → emit → build pipeline**.

Blocks are only registered on a project when their frame's factory is already attached (`Project.add_block`). Workspace create/load/delete block ops go through that gate; orchestration stays on `Project` (e.g. `workspace.get_project(...)` then `project.build()`).

---

## Factory packages

Factories are portable `.tar.gz` archives. [`Packager`](../base/Packager.py) handles stage/manifest/pack/unpack; [`Catalog`](../core/Catalog.py) owns `export_factory` / `import_factory`.

**Specs live in the database.** On-disk catalog trees hold artifacts only (`module.py`, concretes, bindings, `base/`). Spec JSON (`factory.json` / `frame.json`) exists only inside packages for transport:

- **Export** — Specs from DB + artifacts from disk → archive (JSON written into the package only).
- **Import** — Specs from package JSON → DB; artifacts → disk (Spec JSON stripped from the catalog tree).

**Archive layout**

```
MANIFEST.json                 # format_version, name, version, checksums
factory/<name>/<version>/
  factory.json                # factory Spec (transport only)
  frames/<frame>/
    frame.json                # frame Spec (transport only)
    module.py
    concretes/*
    bindings/*
  base/                       # optional clone scaffold
```

| Layer | Role |
|-------|------|
| `utils/fs` | Shared filesystem helpers |
| `Packager` | stage, MANIFEST, pack, unpack |
| `Catalog` | `export_factory` / `import_factory` (DB Specs + disk artifacts) |
| `Factory` | Single factory instance hydrated from DB |

Share factories via export/import. Path traversal and unsupported `format_version` are rejected.

---

## Logging

All application logging goes through [`utils/logger.py`](../utils/logger.py), configured from the `logger` section of `config.yaml` during `server.init()`.

| Severity | Typical use |
|----------|-------------|
| `debug` | Internals: construct/load/validate/decode, type registration, template I/O, soft lookups that return `None` in-memory |
| `info` | Lifecycle boundaries: create/update/delete factory/frame/project/block, pipeline start/end, clone, build, render |
| `warning` | Soft failures before return/`raise`: missing catalog/workspace entity, validation failure about to propagate |
| `error` | Hard failures: pipeline non-zero exit, decode failure, concrete destination unset, shell command failure |
| `critical` | Reserved for unrecoverable process-level failures |

### Layer conventions

| Layer | Prefer | Avoid |
|-------|--------|-------|
| **`base/`** | `debug` for Spec/Schema/Resource/Template internals; `warning`/`error` only on validate/decode/pipeline failure | Spamming `info` on every validate/render leaf |
| **`core/`** | `info` for Catalog/Workspace CRUD and emit/build; `debug` for Frame/Factory/Block construct and in-memory getters | Treating a missing `get_*` that returns `None` as `error` |
| **`utils/`** | `debug` for shell stdout lines; `error` for failed shell commands | |

Hot paths (e.g. `BindingType.validate` during jsonschema checks) stay quiet — log at registration or decode time instead.

`server.log(...)` remains a thin re-export for legacy call sites; prefer `from utils import logger` in new code (`logger.info`, `logger.error`, …).

Set `logger.level: DEBUG` in `config.yaml` (or the console handler level) to see base/core construct and validate traces.

---

## Repository layout

| Path | Role |
|------|------|
| `catalog/` | Factory on-disk layout: frames, concretes, bindings, maps data, base |
| `catalog/schemas/` | JSON schemas that validate factory and frame data |
| `workspace/` | Projects with generated `src/` |
| `core/` | Domain models: `Catalog`, `Workspace`, `Project`, `Factory`, `Frame`, `Block` |
| `base/` | Foundations: `Resource`, `CatalogResource`, `Spec`, `Schema`, `PipelineExecuter`, `DataType`, `Binding` |
| `data/` | SQLite persistence via SQLAlchemy (models + `database.py`) |
| `utils/` | `RuntimeModule`, centralized logger, shell helpers |
| `tests/` | pytest suite |
| `server.py` | Bootstrap: config → logger → database → catalog + workspace |
| `controller.py` | Singleton `Catalog` and `Workspace` |
| `config.yaml` | Catalog path, workspace path, database URL, logger settings |

---

## Resource identifiers

| Resource | Format | Example |
|----------|--------|---------|
| Factory | `name:version` | `backend-fastapi:v1` |
| Frame | `factory:version.frame` | `backend-fastapi:v1.table` |
| Block | `frame_id.block_name` | `backend-fastapi:v1.table.users` |

---

## Running

Requires Python 3.12+ (see project env). Configure `config.yaml`, then:

```bash
python main.py
```

`server.init()` loads the config, sets up the logger (format, datefmt, console/file handlers), auto-creates the database schema, and wires the `Catalog` and `Workspace` singletons.

Run the test suite:

```bash
pytest
```
