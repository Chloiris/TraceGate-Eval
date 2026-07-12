from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tracegate.graph import build_repository_map
from tracegate.indexing import (
    PARSER_CAPABILITY_MATRIX,
    CapabilityStatus,
    ParserFeature,
    RelationStatus,
    RepositoryIndexer,
    SymbolKind,
    UnifiedCodeParser,
    changed_symbols,
    map_changed_symbols,
)
from tracegate.repository import RepositoryBoundary
from tracegate.studio.database import StudioDatabase
from tracegate.studio.index_store import persist_repository_index
from tracegate.studio.migration_runner import upgrade_database
from tracegate.studio.models import IndexedFile, Repository


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "parser_repositories"
LANGUAGES = ("python", "javascript", "typescript", "java")
FEATURE_LABELS = {
    "File recognition": ParserFeature.FILE_RECOGNITION,
    "Import / export": ParserFeature.IMPORT_EXPORT,
    "Class / interface": ParserFeature.CLASS_INTERFACE,
    "Function / method": ParserFeature.FUNCTION_METHOD,
    "Symbol definition": ParserFeature.SYMBOL_DEFINITION,
    "Symbol reference": ParserFeature.SYMBOL_REFERENCE,
    "Inheritance / implementation": ParserFeature.INHERITANCE_IMPLEMENTATION,
    "File-level dependency": ParserFeature.FILE_DEPENDENCY,
    "Function-level call": ParserFeature.FUNCTION_CALL,
    "Test relationship": ParserFeature.TEST_RELATIONSHIP,
    "Changed symbol mapping": ParserFeature.CHANGED_SYMBOL_MAPPING,
    "Line range accuracy": ParserFeature.LINE_RANGE_ACCURACY,
}


def _git(workspace: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repository(tmp_path: Path, language: str) -> Path:
    workspace = tmp_path / language
    shutil.copytree(FIXTURE_ROOT / language, workspace)
    _git(workspace, "init", "-q")
    _git(workspace, "config", "user.email", "parser-tests@tracegate.invalid")
    _git(workspace, "config", "user.name", "TraceGate Parser Tests")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", f"{language} parser fixture")
    return workspace


def _edge_paths(repository_map):  # type: ignore[no-untyped-def]
    nodes = {node.id: node for node in repository_map.nodes}
    return {
        (nodes[edge.source].path, nodes[edge.target].path, edge.kind)
        for edge in repository_map.edges
    }


def test_capability_matrix_is_complete_and_never_overstates_reference_or_call_support() -> None:
    expected_features = set(ParserFeature)
    assert set(PARSER_CAPABILITY_MATRIX) == set(LANGUAGES)
    for language, assessments in PARSER_CAPABILITY_MATRIX.items():
        assert set(assessments) == expected_features
        for assessment in assessments.values():
            assert assessment.status in CapabilityStatus
            if assessment.status == CapabilityStatus.PARTIAL:
                assert assessment.limitation
        if language != "python":
            assert (
                assessments[ParserFeature.SYMBOL_REFERENCE].status
                == CapabilityStatus.UNSUPPORTED
            )
            assert assessments[ParserFeature.FUNCTION_CALL].status == CapabilityStatus.UNSUPPORTED


def test_documented_matrix_matches_machine_readable_statuses() -> None:
    document = (Path(__file__).parents[1] / "docs" / "parser-capability-matrix.md").read_text(
        encoding="utf-8"
    )
    documented: dict[ParserFeature, tuple[str, ...]] = {}
    for line in document.splitlines():
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if cells and cells[0] in FEATURE_LABELS:
            documented[FEATURE_LABELS[cells[0]]] = cells[1:]

    assert set(documented) == set(ParserFeature)
    for feature, statuses in documented.items():
        assert statuses == tuple(
            PARSER_CAPABILITY_MATRIX[language][feature].status.value
            for language in LANGUAGES
        )


@pytest.mark.parametrize(
    ("filename", "language"),
    [
        ("module.py", "python"),
        ("module.js", "javascript"),
        ("module.jsx", "javascript"),
        ("module.ts", "typescript"),
        ("module.tsx", "typescript"),
        ("Module.java", "java"),
    ],
)
def test_file_recognition_is_explicit(filename: str, language: str) -> None:
    assert UnifiedCodeParser().language_for(Path(filename)) == language


def test_unknown_extension_is_not_mislabeled_as_a_supported_language() -> None:
    parsed = UnifiedCodeParser().parse("module.go", "package example")
    assert parsed.language == "unknown"
    assert not parsed.symbols


@pytest.mark.parametrize("language", LANGUAGES)
def test_each_parser_fixture_is_a_real_commit_bound_git_repository(
    tmp_path: Path,
    language: str,
) -> None:
    workspace = _repository(tmp_path, language)
    snapshot = RepositoryIndexer(RepositoryBoundary(workspace)).build()

    assert snapshot.commit_sha == _git(workspace, "rev-parse", "HEAD")
    assert snapshot.files
    assert {item.parsed.language for item in snapshot.files.values()} == {language}


def test_python_ast_definitions_references_relations_and_ranges(tmp_path: Path) -> None:
    workspace = _repository(tmp_path, "python")
    parsed = UnifiedCodeParser().parse(
        "src/service.py",
        (workspace / "src" / "service.py").read_text(encoding="utf-8"),
    )
    symbols = {symbol.qualified_name: symbol for symbol in parsed.symbols}

    assert parsed.imports == (".helper",)
    assert parsed.exports == ()
    assert symbols["BaseService"].kind == SymbolKind.CLASS
    assert (symbols["BaseService"].start_line, symbols["BaseService"].end_line) == (4, 6)
    assert symbols["Service.run"].kind == SymbolKind.METHOD
    assert (symbols["Service.run"].start_line, symbols["Service.run"].end_line) == (10, 11)
    assert symbols["normalize"].kind == SymbolKind.FUNCTION
    assert (symbols["normalize"].start_line, symbols["normalize"].end_line) == (14, 15)
    assert any(
        reference.target == "normalize"
        and reference.resolved
        and reference.status == RelationStatus.CONFIRMED
        for reference in parsed.references
    )
    assert any(
        reference.target == "helper"
        and not reference.resolved
        and reference.status == RelationStatus.UNKNOWN
        for reference in parsed.references
    )
    assert any(
        relation.source_symbol == "Service"
        and relation.target == "BaseService"
        and relation.status == RelationStatus.CONFIRMED
        for relation in parsed.relationships
    )


def test_python_symbol_ranges_include_decorator_lines_exactly() -> None:
    parsed = UnifiedCodeParser().parse(
        "decorated.py",
        """@function_decorator
def decorated():
    return 1

@class_decorator
class Decorated:
    pass
""",
    )
    symbols = {symbol.qualified_name: symbol for symbol in parsed.symbols}

    assert (symbols["decorated"].start_line, symbols["decorated"].end_line) == (1, 3)
    assert (symbols["Decorated"].start_line, symbols["Decorated"].end_line) == (5, 7)
    assert map_changed_symbols(parsed, [1]) == (symbols["decorated"],)
    assert map_changed_symbols(parsed, [5]) == (symbols["Decorated"],)


@pytest.mark.parametrize(
    ("language", "expected_normalize_line"),
    (("javascript", 11), ("typescript", 15)),
)
def test_ecmascript_adapters_report_only_partial_declarations(
    tmp_path: Path,
    language: str,
    expected_normalize_line: int,
) -> None:
    workspace = _repository(tmp_path, language)
    extension = "js" if language == "javascript" else "ts"
    parsed = UnifiedCodeParser().parse(
        f"src/service.{extension}",
        (workspace / "src" / f"service.{extension}").read_text(encoding="utf-8"),
    )

    assert parsed.imports == (f"./helper{'.js' if language == 'javascript' else ''}",)
    assert {"BaseService", "Service", "normalize"} <= set(parsed.exports)
    assert {"BaseService", "Service", "normalize"} <= {symbol.name for symbol in parsed.symbols}
    assert "run" not in {symbol.name for symbol in parsed.symbols}
    assert not parsed.references
    assert parsed.relationships
    assert all(relation.status == RelationStatus.INFERRED for relation in parsed.relationships)
    normalize = next(symbol for symbol in parsed.symbols if symbol.name == "normalize")
    assert (normalize.start_line, normalize.end_line) == (
        expected_normalize_line,
        expected_normalize_line,
    )


def test_typescript_interface_is_detected_but_not_semantically_resolved(tmp_path: Path) -> None:
    workspace = _repository(tmp_path, "typescript")
    parsed = UnifiedCodeParser().parse(
        "src/helper.ts",
        (workspace / "src" / "helper.ts").read_text(encoding="utf-8"),
    )
    source = next(symbol for symbol in parsed.symbols if symbol.name == "ValueSource")
    assert source.kind == SymbolKind.INTERFACE
    assert (source.start_line, source.end_line) == (1, 1)


def test_java_adapter_reports_partial_types_methods_and_inferred_relations(tmp_path: Path) -> None:
    workspace = _repository(tmp_path, "java")
    path = workspace / "src" / "main" / "java" / "com" / "example" / "Service.java"
    parsed = UnifiedCodeParser().parse(
        "src/main/java/com/example/Service.java",
        path.read_text(encoding="utf-8"),
    )

    assert parsed.imports == ("com.example.Helper",)
    assert parsed.exports == ()
    assert {"Service", "run", "value"} <= {symbol.name for symbol in parsed.symbols}
    assert not parsed.references
    assert {relation.kind for relation in parsed.relationships} == {"inherit", "implement"}
    assert all(relation.status == RelationStatus.INFERRED for relation in parsed.relationships)
    run = next(symbol for symbol in parsed.symbols if symbol.name == "run")
    assert (run.start_line, run.end_line) == (6, 6)

    interface_path = workspace / "src" / "main" / "java" / "com" / "example" / "ValueSource.java"
    interface = UnifiedCodeParser().parse(
        "src/main/java/com/example/ValueSource.java",
        interface_path.read_text(encoding="utf-8"),
    )
    value_source = next(symbol for symbol in interface.symbols if symbol.name == "ValueSource")
    assert value_source.kind == SymbolKind.INTERFACE
    assert (value_source.start_line, value_source.end_line) == (3, 3)


def test_java_statements_and_anonymous_classes_do_not_become_method_symbols() -> None:
    parsed = UnifiedCodeParser().parse(
        "Demo.java",
        """public class Demo {
    public int value(int input) {
        return switch (input) {
            default -> 1;
        };
    }

    public Runnable task() {
        return new Runnable() {
            public void run() {}
        };
    }

    record Point(int x) {}
    public return nonsense() {}
    public nonsense junk method() {}
    public int malformed(???) {}
    public int tooMany(int left, int right) {}
    public this fakeThis() {}
    public super fakeSuper() {}
    public instanceof fakeInstanceof() {}
    public break fakeBreak() {}
    public assert fakeAssert() {}
    public goto fakeGoto() {}
    public const fakeConst() {}
    public throws fakeThrows() {}
    public catch fakeCatch() {}
    public int badParameter(int return) {}
}
""",
    )

    assert {symbol.name for symbol in parsed.symbols} == {"Demo", "value", "task"}


def test_java_incomplete_declarations_never_become_symbols() -> None:
    parsed = UnifiedCodeParser().parse(
        "Ghost.java",
        """public class Ghost
public interface Phantom
public class Junk nonsense {}
public class Equals = {}
public interface Bogus bogus {}
public class return {}
public class BadBase extends return {}
""",
    )

    assert parsed.symbols == ()
    assert parsed.relationships == ()
    unclosed = UnifiedCodeParser().parse("Unclosed.java", "public class Unclosed {\n")
    assert unclosed.symbols == ()
    assert unclosed.relationships == ()
    unclosed_method = UnifiedCodeParser().parse(
        "UnclosedMethod.java",
        "public class Carrier {\n    public int ghost() {\n",
    )
    assert unclosed_method.symbols == ()


def test_java_simple_method_subset_does_not_scan_incomplete_lines_quadratically() -> None:
    incomplete_methods = "".join(f"    public int method{index}(\n" for index in range(1000))
    parsed = UnifiedCodeParser().parse(
        "Incomplete.java",
        f"public class Incomplete {{\n{incomplete_methods}}}\n",
    )

    assert parsed.symbols == ()


def test_java_escaped_text_block_delimiter_keeps_embedded_code_masked() -> None:
    parsed = UnifiedCodeParser().parse(
        "TextBlockCarrier.java",
        r'''public class TextBlockCarrier {
    private String text = """
escaped \"""
public class Ghost {}
""";
}
''',
    )

    assert {symbol.name for symbol in parsed.symbols} == {"TextBlockCarrier"}


def test_java_unicode_escape_files_withhold_static_facts_conservatively(
    tmp_path: Path,
) -> None:
    workspace = _repository(tmp_path, "java")
    relative_path = "src/main/java/com/example/UnicodeCarrier.java"
    source = r'''package com.example;
public class UnicodeCarrier {}
\u002f\u002a
public class Ghost {}
\u002a\u002f
'''
    path = workspace / relative_path
    path.write_text(source, encoding="utf-8")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", "add Java Unicode escape case")

    parsed = UnifiedCodeParser().parse(relative_path, source)
    assert parsed.symbols == ()
    assert parsed.imports == ()
    assert parsed.relationships == ()

    repository_map = build_repository_map(
        "java-unicode-escape",
        RepositoryIndexer(RepositoryBoundary(workspace)).build(),
    )
    assert not any(
        node.path == relative_path and node.symbol is not None
        for node in repository_map.nodes
    )


def test_javascript_does_not_invent_interface_declarations() -> None:
    parsed = UnifiedCodeParser().parse("invalid.js", "interface Invented {}\n")

    assert not parsed.symbols
    assert not parsed.relationships


@pytest.mark.parametrize(
    ("relative_path", "content", "expected_import"),
    [
        (
            "module.js",
            'import { helper } from "./helper.js";\n'
            "export const normalize = (value) => { return value; };\n",
            "./helper.js",
        ),
        (
            "module.ts",
            'import { helper } from "./helper";\n'
            "export const normalize = (value: number) => { return helper(value); };\n",
            "./helper",
        ),
    ],
)
def test_ecmascript_claimed_esm_and_parenthesized_arrow_subset_is_explicit(
    relative_path: str,
    content: str,
    expected_import: str,
) -> None:
    parsed = UnifiedCodeParser().parse(relative_path, content)

    assert parsed.imports == (expected_import,)
    normalize = next(symbol for symbol in parsed.symbols if symbol.name == "normalize")
    assert normalize.kind == SymbolKind.FUNCTION
    assert (normalize.start_line, normalize.end_line) == (2, 2)
    assert "normalize" in parsed.exports


def test_commonjs_like_calls_never_become_confirmed_file_dependencies(
    tmp_path: Path,
) -> None:
    workspace = _repository(tmp_path, "javascript")
    source = """const direct = require("./helper.js");
const member = loader.require("./helper.js");
function shadowed(require) {
  return require("./helper.js");
}
"""
    relative_path = "src/require-cases.js"
    path = workspace / relative_path
    path.write_text(source, encoding="utf-8")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", "add untrusted require call shapes")

    parsed = UnifiedCodeParser().parse(relative_path, source)
    assert parsed.imports == ()

    repository_map = build_repository_map(
        "javascript-require-cases",
        RepositoryIndexer(RepositoryBoundary(workspace)).build(),
    )
    source_ids = {
        node.id for node in repository_map.nodes if node.path == relative_path
    }
    assert not any(
        edge.source in source_ids and edge.kind in {"import", "test"}
        for edge in repository_map.edges
    )


def test_malformed_esm_import_and_export_clauses_never_become_static_facts(
    tmp_path: Path,
) -> None:
    workspace = _repository(tmp_path, "javascript")
    relative_path = "src/malformed-module.js"
    source = """import ??? from "./helper.js";
import = from "./helper.js";
import if from "./helper.js";
import { class } from "./helper.js";
import * as return from "./helper.js";
export { ??? };
export { helper as ??? };
export { return };
"""
    path = workspace / relative_path
    path.write_text(source, encoding="utf-8")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", "add malformed ESM clauses")

    parsed = UnifiedCodeParser().parse(relative_path, source)
    assert parsed.imports == ()
    assert parsed.exports == ()

    repository_map = build_repository_map(
        "javascript-malformed-esm",
        RepositoryIndexer(RepositoryBoundary(workspace)).build(),
    )
    source_ids = {
        node.id for node in repository_map.nodes if node.path == relative_path
    }
    assert not any(
        edge.source in source_ids and edge.kind in {"import", "test"}
        for edge in repository_map.edges
    )


@pytest.mark.parametrize(
    ("language", "relative_path"),
    (
        ("javascript", "src/view.jsx"),
        ("typescript", "src/view.tsx"),
    ),
)
def test_jsx_and_tsx_are_recognized_without_confirming_jsx_text_as_code(
    tmp_path: Path,
    language: str,
    relative_path: str,
) -> None:
    workspace = _repository(tmp_path, language)
    source = """export const view = () => (
  <pre>
export class Ghost {}
import { helper } from "./helper";
  </pre>
);
"""
    path = workspace / relative_path
    path.write_text(source, encoding="utf-8")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", f"add {language} JSX text case")

    parsed = UnifiedCodeParser().parse(relative_path, source)
    assert parsed.language == language
    assert parsed.imports == ()
    assert parsed.exports == ()
    assert parsed.symbols == ()

    repository_map = build_repository_map(
        f"{language}-jsx-text",
        RepositoryIndexer(RepositoryBoundary(workspace)).build(),
    )
    assert not any(
        node.path == relative_path and node.symbol == "Ghost"
        for node in repository_map.nodes
    )


def test_ecmascript_adapter_omits_nested_declarations_from_top_level_symbols() -> None:
    parsed = UnifiedCodeParser().parse(
        "module.js",
        """export function outer() {
function nested() {}
}
export function visible() {}
""",
    )

    assert {symbol.name for symbol in parsed.symbols} == {"outer", "visible"}


@pytest.mark.parametrize(
    "content",
    (
        "const wrapped = wrap(\nfunction Ghost() {}\n);\n",
        "const values = [\nclass Ghost {}\n];\n",
        "let target;\ntarget =\nfunction Ghost() {};\n",
        "let target;\ntarget =\nclass Ghost {};\n",
        "let target;\ntarget =\nexport class Ghost {};\n",
    ),
)
def test_ecmascript_expression_continuations_do_not_become_exported_symbols(
    content: str,
) -> None:
    parsed = UnifiedCodeParser().parse("expressions.js", content)

    assert parsed.symbols == ()
    assert parsed.exports == ()


def test_ecmascript_regex_braces_withhold_facts_instead_of_corrupting_scope() -> None:
    sources = (
        """function outer() {
  const closingBrace = /}/;
function Ghost() {}
}
export function visible() {}
""",
        r"""function outer() {
  const escapedClosingSlash = /\}\//;
function Ghost() {}
}
export function visible() {}
""",
    )
    for source in sources:
        parsed = UnifiedCodeParser().parse("module.js", source)
        assert parsed.imports == ()
        assert parsed.exports == ()
        assert parsed.symbols == ()
        assert parsed.relationships == ()


def test_ecmascript_legacy_html_comments_withhold_facts_conservatively() -> None:
    parsed = UnifiedCodeParser().parse(
        "classic.js",
        """function outer() {
<!-- }
function Ghost() {}
}
""",
    )

    assert parsed.imports == ()
    assert parsed.symbols == ()
    assert parsed.relationships == ()


def test_ecmascript_safe_urls_comments_and_division_preserve_exported_symbols() -> None:
    parsed = UnifiedCodeParser().parse(
        "safe-slashes.js",
        """/* documentation for class behavior */
const url = "https://host/class/docs";
const ratio = left / classCount / total;
// see https://host/class/docs
export class Real {}
""",
    )

    assert {symbol.name for symbol in parsed.symbols} == {"Real"}
    assert parsed.exports == ("Real",)


@pytest.mark.parametrize(
    ("relative_path", "content"),
    (
        (
            "invalid.js",
            """export class MissingBody
export function MissingSignature
export class JunkHeader nonsense {}
export class EqualsHeader = {}
export function JunkFunction() nonsense {}
export const junkArrow = () => value ???
export class return {}
export function if() {}
export const class = () => {}
export class BadBase extends return {}
""",
        ),
        (
            "invalid.ts",
            """export interface MissingBody
export const missingArrow = () =>
export interface JunkInterface nonsense {}
export function JunkFunction() nonsense {}
export interface return {}
export function if() {}
export class BadBase extends return {}
""",
        ),
        ("unclosed.js", "export class Unclosed {\n"),
        ("unclosed.ts", "export interface Unclosed {\n"),
        ("unclosed-function.js", "export function unclosed() {\n"),
        ("unclosed-arrow.js", "export const unclosed = () => {\n"),
    ),
)
def test_ecmascript_incomplete_declarations_never_become_symbols(
    relative_path: str,
    content: str,
) -> None:
    parsed = UnifiedCodeParser().parse(relative_path, content)

    assert parsed.symbols == ()
    assert parsed.exports == ()


def test_ecmascript_single_line_import_subset_does_not_scan_across_lines() -> None:
    source = "".join(f"import missing{i}\n" for i in range(2000))
    parsed = UnifiedCodeParser().parse("incomplete-imports.js", source)

    assert parsed.imports == ()
    assert parsed.symbols == ()


def test_python_imported_base_remains_unknown() -> None:
    parsed = UnifiedCodeParser().parse(
        "service.py",
        "from external import ImportedBase\n\nclass Service(ImportedBase):\n    pass\n",
    )

    assert len(parsed.relationships) == 1
    relation = parsed.relationships[0]
    assert relation.target == "ImportedBase"
    assert relation.status == RelationStatus.UNKNOWN


def test_python_module_and_local_rebindings_never_confirm_same_name_edges() -> None:
    parsed = UnifiedCodeParser().parse(
        "rebindings.py",
        """def helper():
    return 1

from external import helper

def caller():
    return helper()

class Base:
    pass

from external import Base

class ModuleChild(Base):
    pass

def parameter_scope(Base):
    class ParameterChild(Base):
        pass

def import_scope():
    from external import Base
    class ImportChild(Base):
        pass

def assignment_scope():
    Base = object
    class AssignmentChild(Base):
        pass

class ClassScope:
    Base = object
    class ClassChild(Base):
        pass

def global_scope():
    global helper, Base
    helper = lambda: 2
    Base = object
    helper()
    class GlobalChild(Base):
        pass

def nonlocal_scope():
    helper = lambda: 2
    Base = object
    def inner():
        nonlocal helper, Base
        helper = lambda: 3
        Base = object
        helper()
        class NonlocalChild(Base):
            pass
""",
    )

    helper_calls = [
        reference
        for reference in parsed.references
        if reference.target == "helper"
        and reference.source_symbol in {"caller", "global_scope", "nonlocal_scope.inner"}
    ]
    assert len(helper_calls) == 3
    assert all(not reference.resolved for reference in helper_calls)
    assert all(reference.status == RelationStatus.UNKNOWN for reference in helper_calls)
    base_relations = [
        relation for relation in parsed.relationships if relation.target == "Base"
    ]
    assert {relation.source_symbol for relation in base_relations} == {
        "ModuleChild",
        "parameter_scope.ParameterChild",
        "import_scope.ImportChild",
        "assignment_scope.AssignmentChild",
        "ClassScope.ClassChild",
        "global_scope.GlobalChild",
        "nonlocal_scope.inner.NonlocalChild",
    }
    assert all(relation.status == RelationStatus.UNKNOWN for relation in base_relations)


def test_python_wildcard_import_taints_unqualified_call_and_base_resolution() -> None:
    parsed = UnifiedCodeParser().parse(
        "wildcard.py",
        """def helper():
    return 1

class Base:
    pass

from external import *

def caller():
    return helper()

class Child(Base):
    pass
""",
    )

    helper_call = next(reference for reference in parsed.references if reference.target == "helper")
    child_base = next(relation for relation in parsed.relationships if relation.target == "Base")
    assert helper_call.status == RelationStatus.UNKNOWN
    assert not helper_call.resolved
    assert child_base.status == RelationStatus.UNKNOWN


def test_python_definition_time_rebinding_taints_later_calls() -> None:
    parsed = UnifiedCodeParser().parse(
        "definition_time.py",
        """def helper():
    return 1

def setter(value=(helper := lambda: 2)):
    return value

def caller():
    return helper()
""",
    )

    helper_call = next(
        reference
        for reference in parsed.references
        if reference.source_symbol == "caller" and reference.target == "helper"
    )
    assert helper_call.status == RelationStatus.UNKNOWN
    assert not helper_call.resolved


def test_python_inheritance_requires_a_visible_preceding_same_file_base() -> None:
    parsed = UnifiedCodeParser().parse(
        "inheritance.py",
        """class LaterChild(LaterBase):
    pass

class LaterBase:
    pass

class FirstScope:
    class ScopedBase:
        pass

class OtherScope:
    class WrongChild(ScopedBase):
        pass
""",
    )

    relationships = {relation.source_symbol: relation for relation in parsed.relationships}
    assert relationships["LaterChild"].status == RelationStatus.UNKNOWN
    assert relationships["OtherScope.WrongChild"].status == RelationStatus.UNKNOWN


def test_python_call_edges_require_body_execution_and_lexical_visibility(
    tmp_path: Path,
) -> None:
    workspace = _repository(tmp_path, "python")
    source = """def helper():
    return 1

def outer():
    def hidden():
        return helper()
    return hidden()

def cross_scope(value=helper()):
    return hidden()

class Container:
    def member(self):
        return 1

    def caller(self):
        return member()
"""
    path = workspace / "src" / "lexical_calls.py"
    path.write_text(source, encoding="utf-8")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", "add Python lexical call cases")

    parsed = UnifiedCodeParser().parse("src/lexical_calls.py", source)
    references = {
        (reference.source_symbol, reference.target): reference
        for reference in parsed.references
    }

    assert ("cross_scope", "helper") not in references
    assert references[("outer.hidden", "helper")].status == RelationStatus.CONFIRMED
    assert references[("outer", "hidden")].status == RelationStatus.CONFIRMED
    assert references[("cross_scope", "hidden")].status == RelationStatus.UNKNOWN
    assert references[("Container.caller", "member")].status == RelationStatus.UNKNOWN

    repository_map = build_repository_map(
        "python-lexical-calls",
        RepositoryIndexer(RepositoryBoundary(workspace)).build(),
    )
    nodes = {node.id: node for node in repository_map.nodes}
    call_pairs = {
        (nodes[edge.source].symbol, nodes[edge.target].symbol)
        for edge in repository_map.edges
        if edge.kind == "call"
        and nodes[edge.source].path == "src/lexical_calls.py"
    }
    assert ("outer.hidden", "helper") in call_pairs
    assert ("outer", "outer.hidden") in call_pairs
    assert ("cross_scope", "outer.hidden") not in call_pairs
    assert ("Container.caller", "Container.member") not in call_pairs


def test_python_nested_functions_and_shadowed_calls_preserve_semantic_provenance(
    tmp_path: Path,
) -> None:
    workspace = _repository(tmp_path, "python")
    source = """def helper():
    return 1

def outer():
    def inner():
        return helper()
    return inner()

class Service:
    def method(self):
        def nested():
            return 2
        return nested()

def parameter_shadow(helper):
    return helper()

def local_shadow():
    helper()
    helper = lambda: 2
    return helper()

def lambda_shadow():
    callback = lambda helper: helper()
    return callback

def match_shadow(value):
    match value:
        case helper:
            return helper()
"""
    path = workspace / "src" / "scopes.py"
    path.write_text(source, encoding="utf-8")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", "add Python scope provenance cases")

    parsed = UnifiedCodeParser().parse("src/scopes.py", source)
    symbols = {symbol.qualified_name: symbol for symbol in parsed.symbols}

    assert symbols["outer"].kind == SymbolKind.FUNCTION
    assert symbols["outer.inner"].kind == SymbolKind.FUNCTION
    assert symbols["Service.method"].kind == SymbolKind.METHOD
    assert symbols["Service.method.nested"].kind == SymbolKind.FUNCTION
    shadowed_sources = {
        "parameter_shadow",
        "local_shadow",
        "lambda_shadow",
        "match_shadow",
    }
    shadowed = [
        reference
        for reference in parsed.references
        if reference.source_symbol in shadowed_sources and reference.target == "helper"
    ]
    assert shadowed
    assert all(not reference.resolved for reference in shadowed)
    assert all(reference.status == RelationStatus.UNKNOWN for reference in shadowed)

    repository_map = build_repository_map(
        "python-shadowing",
        RepositoryIndexer(RepositoryBoundary(workspace)).build(),
    )
    shadowed_node_ids = {
        node.id
        for node in repository_map.nodes
        if node.path == "src/scopes.py" and node.symbol in shadowed_sources
    }
    assert shadowed_node_ids
    assert not any(
        edge.kind == "call" and edge.source in shadowed_node_ids
        for edge in repository_map.edges
    )


@pytest.mark.parametrize(
    ("language", "relative_path", "content", "real_symbols"),
    [
        (
            "javascript",
            "src/non_code.js",
            """/*
import { helper } from "./helper.js";
export class BlockGhost extends BaseService {}
export function blockGhost() {}
*/
const note = "import { helper } from './helper.js'; export class StringGhost {}";
const template = `
export class TemplateGhost {}
import { helper } from "./helper.js";
`;
""",
            set(),
        ),
        (
            "typescript",
            "src/non_code.ts",
            """/*
import { helper } from "./helper";
export interface BlockGhost extends ValueSource {}
export function blockGhost() {}
*/
const note = "import { helper } from './helper'; export class StringGhost {}";
const template = `
export interface TemplateGhost {}
import { helper } from "./helper";
`;
""",
            set(),
        ),
        (
            "java",
            "src/main/java/com/example/CommentCarrier.java",
            '''package com.example;
/*
import com.example.Helper;
public class BlockGhost extends BaseService {
    public int phantom() { return 1; }
}
*/
public class CommentCarrier {
    private String note = "public class StringGhost {}";
    private String text = """
public class TextBlockGhost {}
import com.example.Helper;
""";
}
''',
            {"CommentCarrier"},
        ),
    ],
)
def test_partial_adapters_mask_comments_and_literals_before_confirming_map_facts(
    tmp_path: Path,
    language: str,
    relative_path: str,
    content: str,
    real_symbols: set[str],
) -> None:
    workspace = _repository(tmp_path, language)
    path = workspace / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", f"add {language} non-code masking cases")

    parsed = UnifiedCodeParser().parse(relative_path, content)
    assert parsed.imports == ()
    assert {symbol.name for symbol in parsed.symbols} == real_symbols
    assert not parsed.relationships

    repository_map = build_repository_map(
        f"non-code-{language}",
        RepositoryIndexer(RepositoryBoundary(workspace)).build(),
    )
    fake_names = {
        "BlockGhost",
        "blockGhost",
        "StringGhost",
        "TemplateGhost",
        "TextBlockGhost",
        "phantom",
    }
    assert not fake_names.intersection(node.label for node in repository_map.nodes)
    source_ids = {
        node.id
        for node in repository_map.nodes
        if node.path == relative_path and node.kind in {"file", "test"}
    }
    assert len(source_ids) == 1
    assert not any(
        edge.source in source_ids and edge.kind in {"import", "test"}
        for edge in repository_map.edges
    )


@pytest.mark.parametrize("language", LANGUAGES)
def test_repository_map_emits_only_confirmed_parser_edges(tmp_path: Path, language: str) -> None:
    workspace = _repository(tmp_path, language)
    snapshot = RepositoryIndexer(RepositoryBoundary(workspace)).build()
    repository_map = build_repository_map(f"parser-{language}", snapshot)
    paths = _edge_paths(repository_map)

    assert all(edge.confirmed for edge in repository_map.edges)
    if language == "java":
        assert not any(kind in {"import", "test"} for _source, _target, kind in paths)
    else:
        assert any(kind == "import" for _source, _target, kind in paths)
        assert any(kind == "test" for _source, _target, kind in paths)
    if language == "python":
        assert any(edge.kind == "call" for edge in repository_map.edges)
        assert any(edge.kind == "inherit" for edge in repository_map.edges)
    else:
        assert not any(
            edge.kind in {"call", "inherit", "implement"}
            for edge in repository_map.edges
        )


@pytest.mark.parametrize("language", LANGUAGES)
def test_test_relationship_requires_conventional_test_file_and_resolved_import(
    tmp_path: Path,
    language: str,
) -> None:
    workspace = _repository(tmp_path, language)
    repository_map = build_repository_map(
        f"test-relationship-{language}",
        RepositoryIndexer(RepositoryBoundary(workspace)).build(),
    )
    nodes = {node.id: node for node in repository_map.nodes}
    test_edges = [edge for edge in repository_map.edges if edge.kind == "test"]

    if language == "java":
        assert not test_edges
        return
    assert test_edges
    assert all(nodes[edge.source].kind == "test" for edge in test_edges)
    assert all(nodes[edge.target].kind == "file" for edge in test_edges)


@pytest.mark.parametrize(
    (
        "language",
        "non_test_path",
        "non_test_content",
        "unresolved_test_path",
        "unresolved_test_content",
    ),
    [
        (
            "python",
            "checks/service_check.py",
            "from src.service import Service\n",
            "tests/test_missing.py",
            "from src.missing import Missing\n",
        ),
        (
            "javascript",
            "checks/service-check.js",
            'import { Service } from "../src/service.js";\n',
            "tests/missing.test.js",
            'import { Missing } from "../src/missing.js";\n',
        ),
        (
            "typescript",
            "checks/service-check.ts",
            'import { Service } from "../src/service";\n',
            "tests/missing.spec.ts",
            'import { Missing } from "../src/missing";\n',
        ),
        (
            "java",
            "src/main/java/com/example/ServiceCheck.java",
            "package com.example;\nimport com.example.Service;\npublic class ServiceCheck {}\n",
            "src/test/java/com/example/MissingTest.java",
            "package com.example;\nimport com.example.Missing;\npublic class MissingTest {}\n",
        ),
    ],
)
def test_test_relationship_does_not_promote_non_tests_or_unresolved_imports(
    tmp_path: Path,
    language: str,
    non_test_path: str,
    non_test_content: str,
    unresolved_test_path: str,
    unresolved_test_content: str,
) -> None:
    workspace = _repository(tmp_path, language)
    for relative_path, content in (
        (non_test_path, non_test_content),
        (unresolved_test_path, unresolved_test_content),
    ):
        path = workspace / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", f"add {language} relationship negatives")

    repository_map = build_repository_map(
        f"test-negative-{language}",
        RepositoryIndexer(RepositoryBoundary(workspace)).build(),
    )
    nodes = {node.id: node for node in repository_map.nodes}
    non_test_ids = {node.id for node in repository_map.nodes if node.path == non_test_path}
    unresolved_ids = {
        node.id for node in repository_map.nodes if node.path == unresolved_test_path
    }

    if language == "java":
        assert not any(
            edge.source in non_test_ids and edge.kind in {"import", "test"}
            for edge in repository_map.edges
        )
    else:
        assert any(
            edge.source in non_test_ids
            and edge.kind == "import"
            and nodes[edge.source].kind == "file"
            for edge in repository_map.edges
        )
    assert not any(
        edge.source in unresolved_ids and edge.kind in {"import", "test"}
        for edge in repository_map.edges
    )


def test_python_changed_symbol_mapping_uses_real_git_diff_and_ast_range(tmp_path: Path) -> None:
    workspace = _repository(tmp_path, "python")
    indexer = RepositoryIndexer(RepositoryBoundary(workspace))
    base = indexer.build()
    base_sha = base.commit_sha
    path = workspace / "src" / "service.py"
    path.write_text(
        path.read_text(encoding="utf-8").replace("    return value\n", "    return value + 1\n", 1),
        encoding="utf-8",
    )
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", "change one Python symbol body")
    head = indexer.build(base)
    diff = _git(workspace, "diff", f"{base_sha}...{head.commit_sha}")
    mapped = changed_symbols(head, diff)

    assert [symbol.qualified_name for symbol in mapped["src/service.py"]] == [
        "BaseService",
        "BaseService.identity",
    ]


@pytest.mark.parametrize(
    ("language", "relative_path", "before", "after", "symbol_name"),
    [
        (
            "javascript",
            "src/service.js",
            "export function normalize(value) {",
            "export function normalize(input) {",
            "normalize",
        ),
        (
            "typescript",
            "src/service.ts",
            "export function normalize(value: number): number {",
            "export function normalize(input: number): number {",
            "normalize",
        ),
        (
            "java",
            "src/main/java/com/example/Service.java",
            "    public int run(int value) {",
            "    public final int run(int value) {",
            "run",
        ),
    ],
)
def test_partial_changed_symbol_mapping_uses_real_git_diff_for_declaration_changes(
    tmp_path: Path,
    language: str,
    relative_path: str,
    before: str,
    after: str,
    symbol_name: str,
) -> None:
    workspace = _repository(tmp_path, language)
    indexer = RepositoryIndexer(RepositoryBoundary(workspace))
    base = indexer.build()
    path = workspace / relative_path
    content = path.read_text(encoding="utf-8")
    assert before in content
    path.write_text(content.replace(before, after, 1), encoding="utf-8")
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", f"change {language} declaration")
    head = indexer.build(base)
    diff = _git(workspace, "diff", f"{base.commit_sha}...{head.commit_sha}")
    mapped = changed_symbols(head, diff)

    assert symbol_name in {symbol.name for symbol in mapped[relative_path]}


@pytest.mark.parametrize(
    ("language", "relative_path", "symbol_name", "body_line_offset"),
    [
        ("javascript", "src/service.js", "normalize", 1),
        ("typescript", "src/service.ts", "normalize", 1),
        ("java", "src/main/java/com/example/Service.java", "run", 1),
    ],
)
def test_partial_line_ranges_map_declarations_but_not_function_bodies(
    tmp_path: Path,
    language: str,
    relative_path: str,
    symbol_name: str,
    body_line_offset: int,
) -> None:
    workspace = _repository(tmp_path, language)
    parsed = UnifiedCodeParser().parse(
        relative_path,
        (workspace / relative_path).read_text(encoding="utf-8"),
    )
    symbol = next(item for item in parsed.symbols if item.name == symbol_name)

    assert map_changed_symbols(parsed, [symbol.start_line]) == (symbol,)
    assert map_changed_symbols(parsed, [symbol.start_line + body_line_offset]) == ()


def test_partial_relationship_provenance_survives_incremental_database_index(
    tmp_path: Path,
) -> None:
    workspace = _repository(tmp_path, "typescript")
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'parser.db').as_posix()}"
    upgrade_database(database_url)
    database = StudioDatabase(database_url)
    try:
        with database.session_factory() as session:
            repository = Repository(
                owner="tracegate-tests",
                name="typescript-parser",
                full_name="tracegate-tests/typescript-parser",
                local_path=str(workspace),
                connection_status="ready",
            )
            session.add(repository)
            session.commit()
            session.refresh(repository)
            first, first_map = persist_repository_index(session, repository)
            service = (
                session.query(IndexedFile)
                .filter(
                    IndexedFile.index_version_id == first.id,
                    IndexedFile.path == "src/service.ts",
                )
                .one()
            )
            assert {"BaseService", "Service", "normalize"} <= set(service.exports_json)
            assert {item["status"] for item in service.relationships_json} == {"inferred"}
            assert not any(edge.kind in {"inherit", "implement"} for edge in first_map.edges)

        test_path = workspace / "tests" / "service.spec.ts"
        test_path.write_text(test_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        _git(workspace, "add", ".")
        _git(workspace, "commit", "-qm", "change only test file")

        with database.session_factory() as session:
            repository = session.query(Repository).one()
            second, second_map = persist_repository_index(session, repository)
            service = (
                session.query(IndexedFile)
                .filter(
                    IndexedFile.index_version_id == second.id,
                    IndexedFile.path == "src/service.ts",
                )
                .one()
            )
            assert {item["status"] for item in service.relationships_json} == {"inferred"}
            assert not any(edge.kind in {"inherit", "implement"} for edge in second_map.edges)
    finally:
        database.dispose()
