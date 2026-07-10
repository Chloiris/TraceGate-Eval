from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class LanguageCapability(StrEnum):
    FILE_LEVEL = "file-level"
    SYMBOL_LEVEL = "symbol-level"
    REFERENCE_LEVEL = "reference-level"
    CALL_LEVEL = "call-level"
    PARTIAL_ANALYSIS = "partial-analysis"


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


@dataclass(frozen=True)
class ParsedFile:
    path: str
    language: str
    capabilities: tuple[LanguageCapability, ...]
    imports: tuple[str, ...] = ()
    symbols: tuple[CodeSymbol, ...] = ()
    references: tuple[CodeReference, ...] = ()
    parse_errors: tuple[str, ...] = ()


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
_JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.*]+)\s*;", re.MULTILINE)
_JAVA_TYPE = re.compile(r"^\s*(?:public\s+)?(?:abstract\s+)?(class|interface)\s+(\w+)", re.MULTILINE)
_JAVA_METHOD = re.compile(
    r"^\s*(?:public|protected|private|static|final|synchronized|native|abstract|\s)+"
    r"[\w<>\[\], ?]+\s+(\w+)\s*\([^;{}]*\)\s*(?:throws [^{]+)?\{",
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
            references=tuple(visitor.references),
        )

    def _parse_ecmascript(self, path: str, content: str, language: str) -> ParsedFile:
        imports = tuple(sorted(set(_ECMA_IMPORT.findall(content))))
        symbols: list[CodeSymbol] = []
        for match in _ECMA_SYMBOL.finditer(content):
            declaration, named, arrow = match.groups()
            name = named or arrow
            kind = SymbolKind.CLASS if declaration == "class" else SymbolKind.INTERFACE if declaration == "interface" else SymbolKind.FUNCTION
            line = content.count("\n", 0, match.start()) + 1
            symbols.append(CodeSymbol(name, name, kind, match.group(0).strip(), line, line))
        return ParsedFile(
            path=path,
            language=language,
            capabilities=(
                LanguageCapability.FILE_LEVEL,
                LanguageCapability.SYMBOL_LEVEL,
                LanguageCapability.REFERENCE_LEVEL,
                LanguageCapability.PARTIAL_ANALYSIS,
            ),
            imports=imports,
            symbols=tuple(symbols),
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
        return ParsedFile(
            path=path,
            language="java",
            capabilities=(
                LanguageCapability.FILE_LEVEL,
                LanguageCapability.SYMBOL_LEVEL,
                LanguageCapability.REFERENCE_LEVEL,
                LanguageCapability.PARTIAL_ANALYSIS,
            ),
            imports=imports,
            symbols=tuple(symbols),
        )


@dataclass
class _PythonVisitor(ast.NodeVisitor):
    imports: set[str] = field(default_factory=set)
    symbols: list[CodeSymbol] = field(default_factory=list)
    references: list[CodeReference] = field(default_factory=list)
    scope: list[str] = field(default_factory=list)

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.update(alias.name for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        prefix = "." * node.level
        self.imports.add(prefix + (node.module or ""))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._record_symbol(node, SymbolKind.CLASS, f"class {node.name}")
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
