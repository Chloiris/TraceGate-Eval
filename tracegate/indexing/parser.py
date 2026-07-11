from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Iterable


class LanguageCapability(StrEnum):
    FILE_LEVEL = "file-level"
    SYMBOL_LEVEL = "symbol-level"
    REFERENCE_LEVEL = "reference-level"
    CALL_LEVEL = "call-level"
    PARTIAL_ANALYSIS = "partial-analysis"


class CapabilityStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"


class ParserFeature(StrEnum):
    FILE_RECOGNITION = "file_recognition"
    IMPORT_EXPORT = "import_export"
    CLASS_INTERFACE = "class_interface"
    FUNCTION_METHOD = "function_method"
    SYMBOL_DEFINITION = "symbol_definition"
    SYMBOL_REFERENCE = "symbol_reference"
    INHERITANCE_IMPLEMENTATION = "inheritance_implementation"
    FILE_DEPENDENCY = "file_level_dependency"
    FUNCTION_CALL = "function_level_call"
    TEST_RELATIONSHIP = "test_relationship"
    CHANGED_SYMBOL_MAPPING = "changed_symbol_mapping"
    LINE_RANGE_ACCURACY = "line_range_accuracy"


class RelationStatus(StrEnum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CapabilityAssessment:
    status: CapabilityStatus
    limitation: str = ""


class SymbolKind(StrEnum):
    CLASS = "class"
    INTERFACE = "interface"
    FUNCTION = "function"
    METHOD = "method"


@dataclass(frozen=True)
class CodeSymbol:
    name: str
    qualified_name: str
    kind: SymbolKind
    signature: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class CodeReference:
    source_symbol: str | None
    target: str
    kind: str
    line: int
    resolved: bool = False
    status: RelationStatus = RelationStatus.UNKNOWN


@dataclass(frozen=True)
class TypeRelation:
    source_symbol: str
    target: str
    kind: str
    line: int
    status: RelationStatus = RelationStatus.UNKNOWN


@dataclass(frozen=True)
class ParsedFile:
    path: str
    language: str
    capabilities: tuple[LanguageCapability, ...]
    imports: tuple[str, ...] = ()
    exports: tuple[str, ...] = ()
    symbols: tuple[CodeSymbol, ...] = ()
    references: tuple[CodeReference, ...] = ()
    relationships: tuple[TypeRelation, ...] = ()
    parse_errors: tuple[str, ...] = ()


def _assessment(status: CapabilityStatus, limitation: str = "") -> CapabilityAssessment:
    return CapabilityAssessment(status, limitation)


PARSER_CAPABILITY_MATRIX: dict[str, dict[ParserFeature, CapabilityAssessment]] = {
    "python": {
        ParserFeature.FILE_RECOGNITION: _assessment(CapabilityStatus.SUPPORTED),
        ParserFeature.IMPORT_EXPORT: _assessment(
            CapabilityStatus.PARTIAL,
            "AST imports are captured; __all__ and runtime exports are not modeled.",
        ),
        ParserFeature.CLASS_INTERFACE: _assessment(
            CapabilityStatus.PARTIAL,
            "Classes are supported; Python has no native interface declaration model here.",
        ),
        ParserFeature.FUNCTION_METHOD: _assessment(CapabilityStatus.SUPPORTED),
        ParserFeature.SYMBOL_DEFINITION: _assessment(CapabilityStatus.SUPPORTED),
        ParserFeature.SYMBOL_REFERENCE: _assessment(
            CapabilityStatus.PARTIAL,
            "Only call-site references are recorded; arbitrary name reads are not indexed.",
        ),
        ParserFeature.INHERITANCE_IMPLEMENTATION: _assessment(
            CapabilityStatus.PARTIAL,
            "Only direct same-file base classes are confirmed; imported and dynamic bases remain unknown.",
        ),
        ParserFeature.FILE_DEPENDENCY: _assessment(
            CapabilityStatus.PARTIAL,
            "Only uniquely resolved local Python modules produce confirmed file edges.",
        ),
        ParserFeature.FUNCTION_CALL: _assessment(
            CapabilityStatus.PARTIAL,
            "Only unique direct-name calls to same-file symbols are confirmed.",
        ),
        ParserFeature.TEST_RELATIONSHIP: _assessment(
            CapabilityStatus.PARTIAL,
            "Conventional test paths/names plus a uniquely resolved local import are required.",
        ),
        ParserFeature.CHANGED_SYMBOL_MAPPING: _assessment(
            CapabilityStatus.PARTIAL,
            "Head-side changed lines map to overlapping symbols; deleted symbols are not reconstructed.",
        ),
        ParserFeature.LINE_RANGE_ACCURACY: _assessment(CapabilityStatus.SUPPORTED),
    },
    "javascript": {
        ParserFeature.FILE_RECOGNITION: _assessment(CapabilityStatus.SUPPORTED),
        ParserFeature.IMPORT_EXPORT: _assessment(
            CapabilityStatus.PARTIAL,
            "Common single-line ESM/CommonJS forms only; dynamic and complex multiline forms are excluded.",
        ),
        ParserFeature.CLASS_INTERFACE: _assessment(
            CapabilityStatus.PARTIAL,
            "Top-level classes are detected; JavaScript has no interface declarations.",
        ),
        ParserFeature.FUNCTION_METHOD: _assessment(
            CapabilityStatus.PARTIAL,
            "Top-level function and arrow declarations only; methods are not parsed.",
        ),
        ParserFeature.SYMBOL_DEFINITION: _assessment(
            CapabilityStatus.PARTIAL, "Top-level declaration patterns only."
        ),
        ParserFeature.SYMBOL_REFERENCE: _assessment(CapabilityStatus.UNSUPPORTED),
        ParserFeature.INHERITANCE_IMPLEMENTATION: _assessment(
            CapabilityStatus.PARTIAL,
            "extends syntax is recorded as inferred and never emitted as a confirmed static edge.",
        ),
        ParserFeature.FILE_DEPENDENCY: _assessment(
            CapabilityStatus.PARTIAL, "Only unique relative local imports/requires are confirmed."
        ),
        ParserFeature.FUNCTION_CALL: _assessment(CapabilityStatus.UNSUPPORTED),
        ParserFeature.TEST_RELATIONSHIP: _assessment(
            CapabilityStatus.PARTIAL,
            "Conventional test names plus a unique relative import are required.",
        ),
        ParserFeature.CHANGED_SYMBOL_MAPPING: _assessment(
            CapabilityStatus.PARTIAL, "Only declaration-line overlap is available."
        ),
        ParserFeature.LINE_RANGE_ACCURACY: _assessment(
            CapabilityStatus.PARTIAL, "Only declaration start lines are reported."
        ),
    },
    "typescript": {
        ParserFeature.FILE_RECOGNITION: _assessment(CapabilityStatus.SUPPORTED),
        ParserFeature.IMPORT_EXPORT: _assessment(
            CapabilityStatus.PARTIAL, "Common single-line ESM forms only."
        ),
        ParserFeature.CLASS_INTERFACE: _assessment(
            CapabilityStatus.PARTIAL, "Top-level class/interface declarations only."
        ),
        ParserFeature.FUNCTION_METHOD: _assessment(
            CapabilityStatus.PARTIAL,
            "Top-level function and arrow declarations only; methods are not parsed.",
        ),
        ParserFeature.SYMBOL_DEFINITION: _assessment(
            CapabilityStatus.PARTIAL, "Top-level declaration patterns only."
        ),
        ParserFeature.SYMBOL_REFERENCE: _assessment(CapabilityStatus.UNSUPPORTED),
        ParserFeature.INHERITANCE_IMPLEMENTATION: _assessment(
            CapabilityStatus.PARTIAL,
            "extends/implements syntax is inferred only and never a confirmed static edge.",
        ),
        ParserFeature.FILE_DEPENDENCY: _assessment(
            CapabilityStatus.PARTIAL, "Only unique relative local imports are confirmed."
        ),
        ParserFeature.FUNCTION_CALL: _assessment(CapabilityStatus.UNSUPPORTED),
        ParserFeature.TEST_RELATIONSHIP: _assessment(
            CapabilityStatus.PARTIAL,
            "Conventional test names plus a unique relative import are required.",
        ),
        ParserFeature.CHANGED_SYMBOL_MAPPING: _assessment(
            CapabilityStatus.PARTIAL, "Only declaration-line overlap is available."
        ),
        ParserFeature.LINE_RANGE_ACCURACY: _assessment(
            CapabilityStatus.PARTIAL, "Only declaration start lines are reported."
        ),
    },
    "java": {
        ParserFeature.FILE_RECOGNITION: _assessment(CapabilityStatus.SUPPORTED),
        ParserFeature.IMPORT_EXPORT: _assessment(
            CapabilityStatus.PARTIAL, "Imports are detected; Java has no export declaration model here."
        ),
        ParserFeature.CLASS_INTERFACE: _assessment(
            CapabilityStatus.PARTIAL, "Simple top-level class/interface declarations only."
        ),
        ParserFeature.FUNCTION_METHOD: _assessment(
            CapabilityStatus.PARTIAL, "Simple method declarations only; constructors and complex syntax may be missed."
        ),
        ParserFeature.SYMBOL_DEFINITION: _assessment(
            CapabilityStatus.PARTIAL, "Top-level types and simple method declarations only."
        ),
        ParserFeature.SYMBOL_REFERENCE: _assessment(CapabilityStatus.UNSUPPORTED),
        ParserFeature.INHERITANCE_IMPLEMENTATION: _assessment(
            CapabilityStatus.PARTIAL,
            "extends/implements syntax is inferred only and never a confirmed static edge.",
        ),
        ParserFeature.FILE_DEPENDENCY: _assessment(
            CapabilityStatus.PARTIAL, "Only unique explicit local imports are confirmed."
        ),
        ParserFeature.FUNCTION_CALL: _assessment(CapabilityStatus.UNSUPPORTED),
        ParserFeature.TEST_RELATIONSHIP: _assessment(
            CapabilityStatus.PARTIAL,
            "Conventional test paths/names plus a unique explicit import are required.",
        ),
        ParserFeature.CHANGED_SYMBOL_MAPPING: _assessment(
            CapabilityStatus.PARTIAL, "Only declaration-line overlap is available."
        ),
        ParserFeature.LINE_RANGE_ACCURACY: _assessment(
            CapabilityStatus.PARTIAL, "Only declaration start lines are reported."
        ),
    },
}


def map_changed_symbols(
    parsed_file: ParsedFile,
    changed_lines: Iterable[int],
) -> tuple[CodeSymbol, ...]:
    """Map Head-side changed lines to symbols using only persisted parser ranges."""
    lines = {line for line in changed_lines if line > 0}
    return tuple(
        symbol
        for symbol in parsed_file.symbols
        if any(symbol.start_line <= line <= symbol.end_line for line in lines)
    )


_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
}
_ECMA_IMPORT = re.compile(
    r"(?:import\s+(?:[^;]*?\s+from\s+)?|require\s*\()\s*['\"]([^'\"]+)['\"]"
)
_ECMA_SYMBOL = re.compile(
    r"^\s*(?:export\s+)?(?:(class|interface|function)\s+([A-Za-z_$][\w$]*)|"
    r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)",
    re.MULTILINE,
)
_ECMA_NAMED_EXPORT = re.compile(r"^\s*export\s*\{([^}]+)\}", re.MULTILINE)
_ECMA_TYPE_RELATION = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(class|interface)\s+([A-Za-z_$][\w$]*)"
    r"(?:\s+extends\s+([A-Za-z_$][\w$]*))?"
    r"(?:\s+implements\s+([^\{]+))?",
    re.MULTILINE,
)
_JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.*]+)\s*;", re.MULTILINE)
_JAVA_TYPE = re.compile(r"^\s*(?:public\s+)?(?:abstract\s+)?(class|interface)\s+(\w+)", re.MULTILINE)
_JAVA_METHOD = re.compile(
    r"^\s*(?:public|protected|private|static|final|synchronized|native|abstract|\s)+"
    r"[\w<>\[\], ?]+\s+(\w+)\s*\([^;{}]*\)\s*(?:throws [^{]+)?\{",
    re.MULTILINE,
)
_JAVA_TYPE_RELATION = re.compile(
    r"^\s*(?:public\s+)?(?:abstract\s+)?(class|interface)\s+(\w+)"
    r"(?:\s+extends\s+([\w.]+))?"
    r"(?:\s+implements\s+([^\{]+))?",
    re.MULTILINE,
)


class UnifiedCodeParser:
    """Python AST parser plus explicitly partial JS/TS/Java adapters."""

    def language_for(self, path: Path) -> str | None:
        return _EXTENSIONS.get(path.suffix.casefold())

    def parse(self, relative_path: str, content: str) -> ParsedFile:
        language = self.language_for(Path(relative_path))
        if language is None:
            return ParsedFile(
                path=relative_path,
                language="unknown",
                capabilities=(LanguageCapability.FILE_LEVEL,),
            )
        if language == "python":
            return self._parse_python(relative_path, content)
        if language in {"javascript", "typescript"}:
            return self._parse_ecmascript(relative_path, content, language)
        return self._parse_java(relative_path, content)

    def _parse_python(self, path: str, content: str) -> ParsedFile:
        try:
            tree = ast.parse(content, filename=path)
        except SyntaxError as exc:
            return ParsedFile(
                path=path,
                language="python",
                capabilities=(LanguageCapability.FILE_LEVEL, LanguageCapability.PARTIAL_ANALYSIS),
                parse_errors=(f"SyntaxError line {exc.lineno}: {exc.msg}",),
            )
        visitor = _PythonVisitor()
        visitor.visit(tree)
        symbols_by_name: dict[str, list[CodeSymbol]] = {}
        for symbol in visitor.symbols:
            symbols_by_name.setdefault(symbol.name, []).append(symbol)
        type_symbols_by_name = {
            name: [
                symbol
                for symbol in symbols
                if symbol.kind in {SymbolKind.CLASS, SymbolKind.INTERFACE}
            ]
            for name, symbols in symbols_by_name.items()
        }
        references = tuple(
            CodeReference(
                reference.source_symbol,
                reference.target,
                reference.kind,
                reference.line,
                resolved=(
                    "." not in reference.target
                    and len(symbols_by_name.get(reference.target, [])) == 1
                ),
                status=(
                    RelationStatus.CONFIRMED
                    if "." not in reference.target
                    and len(symbols_by_name.get(reference.target, [])) == 1
                    else RelationStatus.UNKNOWN
                ),
            )
            for reference in visitor.references
        )
        relationships = tuple(
            TypeRelation(
                relation.source_symbol,
                relation.target,
                relation.kind,
                relation.line,
                (
                    RelationStatus.CONFIRMED
                    if "." not in relation.target
                    and len(type_symbols_by_name.get(relation.target, [])) == 1
                    else RelationStatus.UNKNOWN
                ),
            )
            for relation in visitor.relationships
        )
        return ParsedFile(
            path=path,
            language="python",
            capabilities=(
                LanguageCapability.FILE_LEVEL,
                LanguageCapability.SYMBOL_LEVEL,
                LanguageCapability.REFERENCE_LEVEL,
                LanguageCapability.CALL_LEVEL,
            ),
            imports=tuple(sorted(visitor.imports)),
            symbols=tuple(visitor.symbols),
            references=references,
            relationships=relationships,
        )

    def _parse_ecmascript(self, path: str, content: str, language: str) -> ParsedFile:
        imports = tuple(sorted(set(_ECMA_IMPORT.findall(content))))
        symbols: list[CodeSymbol] = []
        exports: set[str] = set()
        for match in _ECMA_SYMBOL.finditer(content):
            declaration, named, arrow = match.groups()
            name = named or arrow
            kind = SymbolKind.CLASS if declaration == "class" else SymbolKind.INTERFACE if declaration == "interface" else SymbolKind.FUNCTION
            line = content.count("\n", 0, match.start()) + 1
            symbols.append(CodeSymbol(name, name, kind, match.group(0).strip(), line, line))
            if match.group(0).lstrip().startswith("export "):
                exports.add(name)
        for match in _ECMA_NAMED_EXPORT.finditer(content):
            for item in match.group(1).split(","):
                exported = item.strip().split(" as ")[-1].strip()
                if exported:
                    exports.add(exported)
        relationships: list[TypeRelation] = []
        for match in _ECMA_TYPE_RELATION.finditer(content):
            _kind, source, parent, implementations = match.groups()
            line = content.count("\n", 0, match.start()) + 1
            if parent:
                relationships.append(
                    TypeRelation(source, parent, "inherit", line, RelationStatus.INFERRED)
                )
            for target in (implementations or "").split(","):
                target = target.strip()
                if target:
                    relationships.append(
                        TypeRelation(source, target, "implement", line, RelationStatus.INFERRED)
                    )
        return ParsedFile(
            path=path,
            language=language,
            capabilities=(
                LanguageCapability.FILE_LEVEL,
                LanguageCapability.SYMBOL_LEVEL,
                LanguageCapability.PARTIAL_ANALYSIS,
            ),
            imports=imports,
            exports=tuple(sorted(exports)),
            symbols=tuple(symbols),
            relationships=tuple(relationships),
        )

    def _parse_java(self, path: str, content: str) -> ParsedFile:
        imports = tuple(sorted(set(_JAVA_IMPORT.findall(content))))
        symbols: list[CodeSymbol] = []
        for match in _JAVA_TYPE.finditer(content):
            kind = SymbolKind.CLASS if match.group(1) == "class" else SymbolKind.INTERFACE
            line = content.count("\n", 0, match.start()) + 1
            symbols.append(CodeSymbol(match.group(2), match.group(2), kind, match.group(0).strip(), line, line))
        for match in _JAVA_METHOD.finditer(content):
            line = content.count("\n", 0, match.start()) + 1
            symbols.append(CodeSymbol(match.group(1), match.group(1), SymbolKind.METHOD, match.group(0).strip(), line, line))
        relationships: list[TypeRelation] = []
        for match in _JAVA_TYPE_RELATION.finditer(content):
            _kind, source, parent, implementations = match.groups()
            line = content.count("\n", 0, match.start()) + 1
            if parent:
                relationships.append(
                    TypeRelation(source, parent, "inherit", line, RelationStatus.INFERRED)
                )
            for target in (implementations or "").split(","):
                target = target.strip()
                if target:
                    relationships.append(
                        TypeRelation(source, target, "implement", line, RelationStatus.INFERRED)
                    )
        return ParsedFile(
            path=path,
            language="java",
            capabilities=(
                LanguageCapability.FILE_LEVEL,
                LanguageCapability.SYMBOL_LEVEL,
                LanguageCapability.PARTIAL_ANALYSIS,
            ),
            imports=imports,
            symbols=tuple(symbols),
            relationships=tuple(relationships),
        )


@dataclass
class _PythonVisitor(ast.NodeVisitor):
    imports: set[str] = field(default_factory=set)
    symbols: list[CodeSymbol] = field(default_factory=list)
    references: list[CodeReference] = field(default_factory=list)
    relationships: list[TypeRelation] = field(default_factory=list)
    scope: list[str] = field(default_factory=list)

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.update(alias.name for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        prefix = "." * node.level
        self.imports.add(prefix + (node.module or ""))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._record_symbol(node, SymbolKind.CLASS, f"class {node.name}")
        source = ".".join([*self.scope, node.name])
        for base in node.bases:
            target = self._call_name(base)
            if target:
                self.relationships.append(
                    TypeRelation(source, target, "inherit", node.lineno, RelationStatus.UNKNOWN)
                )
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        kind = SymbolKind.METHOD if self.scope else SymbolKind.FUNCTION
        arguments = [argument.arg for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)]
        if node.args.vararg:
            arguments.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            arguments.append(f"**{node.args.kwarg.arg}")
        self._record_symbol(node, kind, f"{node.name}({', '.join(arguments)})")
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        target = self._call_name(node.func)
        if target:
            self.references.append(
                CodeReference(".".join(self.scope) or None, target, "call", node.lineno, False)
            )
        self.generic_visit(node)

    def _record_symbol(self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef, kind: SymbolKind, signature: str) -> None:
        qualified = ".".join([*self.scope, node.name])
        self.symbols.append(
            CodeSymbol(
                node.name,
                qualified,
                kind,
                signature,
                node.lineno,
                getattr(node, "end_lineno", node.lineno),
            )
        )

    @staticmethod
    def _call_name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = _PythonVisitor._call_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return None
