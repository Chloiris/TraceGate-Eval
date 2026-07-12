# Parser capability matrix

Last verified: 2026-07-12. This document describes the checked-in parser as it
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
| Symbol definition | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| Symbol reference | PARTIAL | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| Inheritance / implementation | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| File-level dependency | PARTIAL | PARTIAL | PARTIAL | UNSUPPORTED |
| Function-level call | PARTIAL | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| Test relationship | PARTIAL | PARTIAL | PARTIAL | UNSUPPORTED |
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
- Recorded CodeSymbols are limited to classes, functions, async functions and
  methods; variables, constants, import aliases and assigned lambdas are not
  symbol definitions in this adapter.
- Definition ranges use the earliest decorator line (when present), `lineno`
  and `end_lineno`.
- Calls in function bodies are recorded, but only unique, lexically visible,
  unshadowed direct-name calls to a symbol declared in the same file become
  confirmed call edges. A name rebound at module scope, or bound by a
  current/enclosing function or lambda parameter, assignment, pattern or
  import, remains `unknown`; a wildcard import taints every unqualified target.
  Calls in
  decorators/default expressions, attribute calls, aliases, dispatch and
  runtime monkey-patching are not resolved.
- A direct base class becomes a confirmed inheritance edge only when exactly
  one visible matching class was declared earlier in the same file. Imported,
  later, cross-class-scope and dynamic bases remain `unknown`.
- Python classes are supported; this parser does not invent a native interface
  construct. `__all__` and runtime export behavior are not modeled.

### JavaScript

JavaScript is a declaration-level regular-expression adapter, not an AST and
not a call-graph engine.

- A line-preserving lexical pass masks comments, quoted strings and template
  literals before declaration matching. Import matching retains real module
  specifier strings but rejects a keyword that starts inside a literal.
- Common top-level single-line ESM imports, exported top-level
  classes/functions and block-bodied arrows with zero or one simple parameter
  are partial. Confirmed matches require start-of-file or a preceding
  non-whitespace `;`/`}` boundary and balanced braces/parentheses/brackets;
  valid semicolonless adjacency can therefore be omitted.
- CommonJS `require`, methods, arbitrary symbol references, function calls,
  dynamic imports, nested declarations, complex multiline syntax, re-exports
  and runtime module resolution are not resolved.
- `.jsx` files are recognized as JavaScript, but declaration/import extraction
  is withheld because the bounded adapter is not JSX-aware; JSX text therefore
  cannot create confirmed symbols or dependencies.
- JavaScript `interface` text is not accepted as a declaration. The adapter is
  still not a grammar parser. Bounded header/delimiter failures and
  regular-expression-literal brace/static-syntax ambiguity withhold the file's
  static facts, but declaration-body grammar is not validated.
- Classic-script Annex-B HTML comment syntax also causes the file's facts to
  be withheld because this adapter does not tokenize that legacy form.
- `extends` syntax is stored as `inferred`; it is never a confirmed static map
  edge.
- Symbol ranges cover only the declaration line.

### TypeScript

TypeScript shares the declaration-level ECMAScript adapter and its
line-preserving comment/string/template masking.

- Common single-line imports/exports and explicitly exported top-level class,
  interface, function and block-bodied arrow declarations with zero or one
  simply typed parameter are partial; the same explicit `;`/`}` boundary and
  balanced-delimiter rules apply, so valid semicolonless adjacency can be
  omitted.
- Methods, overloads, namespaces, generics, type references, path aliases,
  project references and function calls are not semantically resolved.
- `extends` and `implements` syntax is stored as `inferred`; neither becomes a
  confirmed static map edge.
- This remains a pattern adapter rather than TypeScript grammar/type analysis;
  bounded header/delimiter failures and regular-expression-literal
  brace/static-syntax ambiguity withhold facts, but declaration-body grammar is
  not validated.
- `.tsx` files are recognized as TypeScript, but extraction is withheld so JSX
  text cannot be promoted to a static fact.
- Symbol ranges cover only the declaration line.

### Java

Java is also a declaration-level regular-expression adapter. A line-preserving
lexical pass masks line/block comments, character/string literals and text
blocks before declaration/import matching.

- Explicit imports, simple top-level class/interface declarations and
  brace-bodied methods with a bounded return type and zero or one simple
  parameter are partial. Static facts require balanced delimiters and a bounded
  declaration boundary.
- Constructors, nested/anonymous types, overload resolution, static imports,
  wildcard resolution, method references and function calls are not resolved.
- `extends` and `implements` syntax is stored as `inferred`; neither becomes a
  confirmed static map edge.
- Java has no export declaration model in this parser. Symbol ranges cover only
  the declaration line.
- Explicit imports remain syntactic observations only. Because package/type
  declarations are not persisted for target validation, Java imports and test
  paths never become confirmed file/test edges.
- Files containing Java Unicode escapes are recognized but all static fact
  extraction is withheld because compiler pretranslation can change comment,
  quote and identifier tokenization without preserving source offsets.
- Declaration bodies are not Java grammar-validated; only the bounded header,
  lexical masking, delimiter and statement-boundary contract is claimed.

## Confirmed-edge policy

Repository Map, Review Map and graph traversal tools accept only confirmed
static edges:

- `contains`: a parsed repository/directory/file/symbol containment fact;
- `import`: a unique exact local-module resolution for Python/JavaScript/
  TypeScript; Java package targets are not confirmed;
- `test`: a conventional test path/name plus a unique exact confirmed local
  import (therefore unsupported for Java);
- `call`: a Python AST function-body direct-name call uniquely resolved to a
  lexically visible same-file symbol and not shadowed by an enclosing function
  or lambda binding;
- `inherit`: a Python AST base resolved to a visible preceding same-file type.

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
represented as a real repository/model result. Regression cases verify exact
reported declaration lines, real Git changed-line mapping, non-code masking,
scope-shadowed Python calls and omission of inferred relations from static
maps. These tests validate parser/index semantics; they do not claim that the
minimal fixture projects are full application build matrices.

Verification command:

```bash
uv run pytest -q \
  tests/test_parser_capability_matrix.py \
  tests/test_indexing_graph.py \
  tests/test_studio_database.py \
  tests/test_studio_api.py \
  tests/test_tool_registry.py
```
