# Parser capability matrix

Last verified: 2026-07-11. This document describes the checked-in parser as it
exists now; it is not a roadmap claim.

Status meanings:

- `SUPPORTED`: the bounded behavior is implemented and verified by an
  automated parser/index/graph test.
- `PARTIAL`: a tested subset exists, and the limitation below is part of the
  product contract.
- `UNSUPPORTED`: no production capability or confirmed static edge is claimed.

## Matrix

| Capability | Python | JavaScript | TypeScript | Java |
| --- | --- | --- | --- | --- |
| File recognition | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED |
| Import / export | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| Class / interface | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| Function / method | SUPPORTED | PARTIAL | PARTIAL | PARTIAL |
| Symbol definition | SUPPORTED | PARTIAL | PARTIAL | PARTIAL |
| Symbol reference | PARTIAL | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| Inheritance / implementation | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| File-level dependency | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| Function-level call | PARTIAL | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| Test relationship | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| Changed symbol mapping | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| Line range accuracy | SUPPORTED | PARTIAL | PARTIAL | PARTIAL |

The machine-readable source for this table is
`tracegate.indexing.PARSER_CAPABILITY_MATRIX`. Tests require every language to
have an assessment for every row and require a non-empty limitation for every
`PARTIAL` assessment.

## Language boundaries

### Python

Python uses the standard-library AST.

- Imports, classes, functions and methods are syntactic AST results.
- Definition start/end lines use `lineno` and `end_lineno`.
- Call references are recorded, but only unique direct-name calls to a symbol
  declared in the same file become confirmed call edges. Attribute calls,
  imported calls, aliases, decorators, dispatch and runtime monkey-patching
  remain `unknown`.
- A direct base class becomes a confirmed inheritance edge only when exactly
  one matching class is declared in the same file. Imported and dynamic bases
  remain `unknown`.
- Python classes are supported; this parser does not invent a native interface
  construct. `__all__` and runtime export behavior are not modeled.

### JavaScript

JavaScript is a declaration-level regular-expression adapter, not an AST and
not a call-graph engine.

- Common single-line ESM imports, CommonJS `require`, exported top-level
  classes/functions and arrow declarations are partial.
- Methods, arbitrary symbol references, function calls, dynamic imports,
  complex multiline syntax, re-exports and runtime module resolution are not
  resolved.
- `extends` syntax is stored as `inferred`; it is never a confirmed static map
  edge.
- Symbol ranges cover only the declaration line.

### TypeScript

TypeScript shares the declaration-level ECMAScript adapter.

- Common single-line imports/exports and top-level class, interface, function
  and arrow declarations are partial.
- Methods, overloads, namespaces, generics, type references, path aliases,
  project references and function calls are not semantically resolved.
- `extends` and `implements` syntax is stored as `inferred`; neither becomes a
  confirmed static map edge.
- Symbol ranges cover only the declaration line.

### Java

Java is also a declaration-level regular-expression adapter.

- Explicit imports, simple top-level class/interface declarations and simple
  method declarations are partial.
- Constructors, nested/anonymous types, overload resolution, static imports,
  wildcard resolution, method references and function calls are not resolved.
- `extends` and `implements` syntax is stored as `inferred`; neither becomes a
  confirmed static map edge.
- Java has no export declaration model in this parser. Symbol ranges cover only
  the declaration line.

## Confirmed-edge policy

Repository Map, Review Map and graph traversal tools accept only confirmed
static edges:

- `contains`: a parsed repository/directory/file/symbol containment fact;
- `import`: a unique exact local-module resolution;
- `test`: a conventional test path/name plus a unique exact local import;
- `call`: a Python AST direct-name call uniquely resolved in the same file;
- `inherit`: a Python AST base uniquely resolved in the same file.

Ambiguous, external, dynamic or regex-only inheritance/implementation
relationships are `inferred` or `unknown` in parser provenance and are omitted
from static maps. Review Map expansion defensively filters `confirmed=false`
rows even if an older or externally inserted row exists. LLM explanations and
Agent Findings are separate evidence overlays; they cannot create or upgrade a
static parser edge.

## Changed symbols and tests

Changed lines come from the real Base-to-Head Git unified diff. Only Head-side
added/replacement lines are intersected with parser-reported symbol ranges.
Python therefore maps body changes to the enclosing method/class. The current
JS/TS/Java declaration-only ranges can map a changed declaration line but not a
body-only edit. Deleted symbols are not reconstructed from the Base snapshot,
so changed-symbol mapping remains `PARTIAL` for every language.

Minimal sources live under `tests/fixtures/parser_repositories/{python,javascript,typescript,java}`.
Tests copy each directory to a temporary location, initialize a real Git
repository, create commits and run the production parser/index/graph code. The
fixtures are parser-test-only and must not be used as product demo data or
represented as a real repository/model result.

Verification command:

```bash
uv run pytest -q \
  tests/test_parser_capability_matrix.py \
  tests/test_indexing_graph.py \
  tests/test_studio_database.py \
  tests/test_studio_api.py \
  tests/test_tool_registry.py
```
