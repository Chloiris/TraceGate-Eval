from __future__ import annotations

import ast
import re
from bisect import bisect_right
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


@dataclass(frozen=True)
class _MaskedSource:
    """Line-preserving lexical masks used by the partial regex adapters."""

    code: str
    comments_only: str
    literal_spans: tuple[tuple[int, int], ...]

    def position_is_literal(self, position: int) -> bool:
        candidate = bisect_right(
            self.literal_spans,
            (position, len(self.code) + 1),
        ) - 1
        return (
            candidate >= 0
            and self.literal_spans[candidate][0]
            <= position
            < self.literal_spans[candidate][1]
        )


@dataclass(frozen=True)
class _PythonReference:
    source_symbol: str | None
    target: str
    kind: str
    line: int
    shadowed: bool = False


@dataclass(frozen=True)
class _PythonTypeRelation:
    source_symbol: str
    target: str
    kind: str
    line: int
    shadowed: bool = False


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
        ParserFeature.SYMBOL_DEFINITION: _assessment(
            CapabilityStatus.PARTIAL,
            "AST class, function, async-function and method definitions only; variables, "
            "constants, import aliases and assigned lambdas are not CodeSymbols.",
        ),
        ParserFeature.SYMBOL_REFERENCE: _assessment(
            CapabilityStatus.PARTIAL,
            "Only call-site references are recorded; module or local rebinding keeps direct "
            "names unknown, wildcard imports taint unqualified names, and arbitrary name reads "
            "are not indexed.",
        ),
        ParserFeature.INHERITANCE_IMPLEMENTATION: _assessment(
            CapabilityStatus.PARTIAL,
            "Only visible, preceding direct same-file base classes are confirmed; imported, "
            "cross-scope and dynamic bases remain unknown.",
        ),
        ParserFeature.FILE_DEPENDENCY: _assessment(
            CapabilityStatus.PARTIAL,
            "Only uniquely resolved local Python modules produce confirmed file edges.",
        ),
        ParserFeature.FUNCTION_CALL: _assessment(
            CapabilityStatus.PARTIAL,
            "Only function-body calls to unique, lexically visible, unshadowed direct-name "
            "same-file symbols are confirmed.",
        ),
        ParserFeature.TEST_RELATIONSHIP: _assessment(
            CapabilityStatus.PARTIAL,
            "Conventional test paths/names plus a uniquely resolved local import are required.",
        ),
        ParserFeature.CHANGED_SYMBOL_MAPPING: _assessment(
            CapabilityStatus.PARTIAL,
            "Head-side changed lines map to overlapping symbols; deleted symbols are not "
            "reconstructed.",
        ),
        ParserFeature.LINE_RANGE_ACCURACY: _assessment(CapabilityStatus.SUPPORTED),
    },
    "javascript": {
        ParserFeature.FILE_RECOGNITION: _assessment(CapabilityStatus.SUPPORTED),
        ParserFeature.IMPORT_EXPORT: _assessment(
            CapabilityStatus.PARTIAL,
            "Common top-level single-line ESM forms after lexical comment/literal masking only; "
            "CommonJS, dynamic and complex multiline forms are excluded, and .jsx extraction "
            "is withheld.",
        ),
        ParserFeature.CLASS_INTERFACE: _assessment(
            CapabilityStatus.PARTIAL,
            "Explicitly exported top-level .js classes with a same-line opening brace are "
            "detected; .jsx extraction is withheld and JavaScript has no interfaces.",
        ),
        ParserFeature.FUNCTION_METHOD: _assessment(
            CapabilityStatus.PARTIAL,
            "Explicitly exported top-level .js functions and block-bodied arrows with zero or "
            "one simple parameter only; methods are not parsed and .jsx extraction is withheld.",
        ),
        ParserFeature.SYMBOL_DEFINITION: _assessment(
            CapabilityStatus.PARTIAL,
            "Explicitly exported top-level declaration patterns after lexical masking only; this "
            "is not full grammar validation.",
        ),
        ParserFeature.SYMBOL_REFERENCE: _assessment(CapabilityStatus.UNSUPPORTED),
        ParserFeature.INHERITANCE_IMPLEMENTATION: _assessment(
            CapabilityStatus.PARTIAL,
            "extends syntax is recorded as inferred and never emitted as a confirmed static edge.",
        ),
        ParserFeature.FILE_DEPENDENCY: _assessment(
            CapabilityStatus.PARTIAL, "Only unique relative top-level ESM imports are confirmed."
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
            CapabilityStatus.PARTIAL,
            "Common top-level single-line ESM forms in .ts files after lexical masking only; "
            ".tsx extraction is withheld.",
        ),
        ParserFeature.CLASS_INTERFACE: _assessment(
            CapabilityStatus.PARTIAL,
            "Explicitly exported top-level .ts class/interface declarations only; .tsx "
            "extraction is withheld.",
        ),
        ParserFeature.FUNCTION_METHOD: _assessment(
            CapabilityStatus.PARTIAL,
            "Explicitly exported top-level .ts functions and block-bodied arrows with zero or one "
            "simply typed parameter only; methods are not parsed and .tsx extraction is withheld.",
        ),
        ParserFeature.SYMBOL_DEFINITION: _assessment(
            CapabilityStatus.PARTIAL,
            "Explicitly exported top-level declaration patterns after lexical masking only; this "
            "is not full grammar validation.",
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
            CapabilityStatus.PARTIAL,
            "Imports are detected after lexical comment/literal masking; Java has no export "
            "declaration model here, and Unicode-escape files are withheld.",
        ),
        ParserFeature.CLASS_INTERFACE: _assessment(
            CapabilityStatus.PARTIAL, "Simple top-level class/interface declarations only."
        ),
        ParserFeature.FUNCTION_METHOD: _assessment(
            CapabilityStatus.PARTIAL,
            "Brace-bodied methods with a bounded return type and zero or one simple parameter "
            "only; constructors, abstract declarations and complex signatures are omitted.",
        ),
        ParserFeature.SYMBOL_DEFINITION: _assessment(
            CapabilityStatus.PARTIAL,
            "Top-level types and simple method declarations after lexical comment/literal masking "
            "only; this is not full grammar validation.",
        ),
        ParserFeature.SYMBOL_REFERENCE: _assessment(CapabilityStatus.UNSUPPORTED),
        ParserFeature.INHERITANCE_IMPLEMENTATION: _assessment(
            CapabilityStatus.PARTIAL,
            "extends/implements syntax is inferred only and never a confirmed static edge.",
        ),
        ParserFeature.FILE_DEPENDENCY: _assessment(
            CapabilityStatus.UNSUPPORTED,
        ),
        ParserFeature.FUNCTION_CALL: _assessment(CapabilityStatus.UNSUPPORTED),
        ParserFeature.TEST_RELATIONSHIP: _assessment(
            CapabilityStatus.UNSUPPORTED,
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
    r"^[ \t]*import[ \t]+(?:['\"]([^'\"\r\n]+)['\"]|"
    r"(?:[A-Za-z_$][\w$]*|"
    r"\{[ \t]*(?:[A-Za-z_$][\w$]*(?:[ \t]+as[ \t]+[A-Za-z_$][\w$]*)?"
    r"(?:[ \t]*,[ \t]*[A-Za-z_$][\w$]*(?:[ \t]+as[ \t]+[A-Za-z_$][\w$]*)?)*)?"
    r"[ \t]*\}|\*[ \t]+as[ \t]+[A-Za-z_$][\w$]*|"
    r"[A-Za-z_$][\w$]*[ \t]*,[ \t]*(?:"
    r"\{[ \t]*(?:[A-Za-z_$][\w$]*(?:[ \t]+as[ \t]+[A-Za-z_$][\w$]*)?"
    r"(?:[ \t]*,[ \t]*[A-Za-z_$][\w$]*(?:[ \t]+as[ \t]+[A-Za-z_$][\w$]*)?)*)?"
    r"[ \t]*\}|\*[ \t]+as[ \t]+[A-Za-z_$][\w$]*))"
    r"[ \t]+from[ \t]+['\"]([^'\"\r\n]+)['\"])[ \t]*;?[ \t]*$",
    re.MULTILINE,
)
_ECMA_SYMBOL = re.compile(
    r"^[ \t]*export[ \t]+(?:(class|interface)[ \t]+([A-Za-z_$][\w$]*)"
    r"(?:[ \t]+extends[ \t]+([A-Za-z_$][\w$]*))?"
    r"(?:[ \t]+implements[ \t]+([A-Za-z_$][\w$]*"
    r"(?:[ \t]*,[ \t]*[A-Za-z_$][\w$]*)*))?[ \t]*\{|"
    r"(function)[ \t]+([A-Za-z_$][\w$]*)[ \t]*\("
    r"[ \t]*(?:([A-Za-z_$][\w$]*)(?:[ \t]*:[ \t]*([A-Za-z_$][\w$]*))?)?"
    r"[ \t]*\)(?:[ \t]*:[ \t]*([A-Za-z_$][\w$]*))?[ \t]*\{|"
    r"(?:const|let|var)[ \t]+([A-Za-z_$][\w$]*)[ \t]*=[ \t]*(?:async[ \t]+)?"
    r"\([ \t]*(?:([A-Za-z_$][\w$]*)(?:[ \t]*:[ \t]*([A-Za-z_$][\w$]*))?)?"
    r"[ \t]*\)[ \t]*=>[ \t]*\{)",
    re.MULTILINE,
)
_ECMA_NAMED_EXPORT = re.compile(
    r"^[ \t]*export[ \t]*\{([ \t]*(?:[A-Za-z_$][\w$]*"
    r"(?:[ \t]+as[ \t]+[A-Za-z_$][\w$]*)?(?:[ \t]*,[ \t]*"
    r"[A-Za-z_$][\w$]*(?:[ \t]+as[ \t]+[A-Za-z_$][\w$]*)?)*)?[ \t]*)\}"
    r"[ \t]*;?[ \t]*$",
    re.MULTILINE,
)
_ECMA_TYPE_RELATION = re.compile(
    r"^[ \t]*export[ \t]+(?:default[ \t]+)?(class|interface)[ \t]+"
    r"([A-Za-z_$][\w$]*)(?:[ \t]+extends[ \t]+([A-Za-z_$][\w$]*))?"
    r"(?:[ \t]+implements[ \t]+([A-Za-z_$][\w$]*"
    r"(?:[ \t]*,[ \t]*[A-Za-z_$][\w$]*)*))?[ \t]*\{",
    re.MULTILINE,
)
_ECMA_HTML_COMMENT = re.compile(r"<!--|^[ \t]*-->", re.MULTILINE)
_JAVA_IMPORT = re.compile(
    r"^[ \t]*import[ \t]+(?:static[ \t]+)?"
    r"([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*(?:\.\*)?)[ \t]*;[ \t]*$",
    re.MULTILINE,
)
_JAVA_TYPE = re.compile(
    r"^[ \t]*(?:public[ \t]+)?(?:abstract[ \t]+)?(class|interface)[ \t]+"
    r"([A-Za-z_$][\w$]*)(?:[ \t]+extends[ \t]+([A-Za-z_$][\w$.]*))?"
    r"(?:[ \t]+implements[ \t]+([A-Za-z_$][\w$.]*"
    r"(?:[ \t]*,[ \t]*[A-Za-z_$][\w$.]*)*))?[ \t]*\{",
    re.MULTILINE,
)
_JAVA_METHOD = re.compile(
    r"^[ \t]*(?:(?:public|protected|private|static|final|synchronized|native|abstract)[ \t]+)*"
    r"([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*(?:<[\w$?.,<>]+>)?(?:\[\])*)"
    r"[ \t]+([A-Za-z_$][\w$]*)[ \t]*\([ \t]*(?:"
    r"([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*(?:<[\w$?.,<>]+>)?(?:\[\])*)"
    r"[ \t]+([A-Za-z_$][\w$]*))?[ \t]*\)[ \t]*"
    r"(?:throws[ \t]+([A-Za-z_$][\w$.]*"
    r"(?:[ \t]*,[ \t]*[A-Za-z_$][\w$.]*)*))?[ \t]*\{",
    re.MULTILINE,
)
_JAVA_TYPE_RELATION = re.compile(
    r"^[ \t]*(?:public[ \t]+)?(?:abstract[ \t]+)?(class|interface)[ \t]+"
    r"([A-Za-z_$][\w$]*)(?:[ \t]+extends[ \t]+([A-Za-z_$][\w$.]*))?"
    r"(?:[ \t]+implements[ \t]+([A-Za-z_$][\w$.]*"
    r"(?:[ \t]*,[ \t]*[A-Za-z_$][\w$.]*)*))?[ \t]*\{",
    re.MULTILINE,
)
_JAVA_UNICODE_ESCAPE = re.compile(r"\\u+[0-9a-fA-F]{4}")
_JAVA_NON_METHOD_PREFIXES = {
    "case",
    "default",
    "do",
    "else",
    "for",
    "if",
    "import",
    "interface",
    "new",
    "record",
    "return",
    "class",
    "enum",
    "extends",
    "implements",
    "package",
    "switch",
    "throw",
    "try",
    "while",
    "yield",
}
_ECMA_RESERVED_IDENTIFIERS = {
    "abstract",
    "any",
    "as",
    "asserts",
    "await",
    "bigint",
    "boolean",
    "break",
    "case",
    "catch",
    "class",
    "const",
    "constructor",
    "continue",
    "debugger",
    "declare",
    "default",
    "delete",
    "do",
    "else",
    "enum",
    "export",
    "extends",
    "false",
    "finally",
    "for",
    "from",
    "function",
    "get",
    "if",
    "implements",
    "import",
    "in",
    "infer",
    "instanceof",
    "interface",
    "is",
    "keyof",
    "let",
    "module",
    "namespace",
    "never",
    "new",
    "null",
    "number",
    "object",
    "of",
    "override",
    "package",
    "private",
    "protected",
    "public",
    "readonly",
    "require",
    "return",
    "satisfies",
    "set",
    "static",
    "string",
    "super",
    "switch",
    "symbol",
    "this",
    "throw",
    "true",
    "try",
    "type",
    "typeof",
    "undefined",
    "unique",
    "unknown",
    "using",
    "var",
    "void",
    "while",
    "with",
    "yield",
}
_ECMA_ALLOWED_SIMPLE_TYPES = {
    "any",
    "bigint",
    "boolean",
    "never",
    "number",
    "object",
    "string",
    "symbol",
    "undefined",
    "unknown",
    "void",
}
_JAVA_RESERVED_IDENTIFIERS = {
    "abstract",
    "assert",
    "boolean",
    "break",
    "byte",
    "case",
    "catch",
    "char",
    "class",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "exports",
    "extends",
    "false",
    "final",
    "finally",
    "float",
    "for",
    "goto",
    "if",
    "implements",
    "import",
    "instanceof",
    "int",
    "interface",
    "long",
    "module",
    "native",
    "new",
    "non-sealed",
    "null",
    "open",
    "opens",
    "package",
    "permits",
    "private",
    "protected",
    "provides",
    "public",
    "record",
    "requires",
    "return",
    "sealed",
    "short",
    "static",
    "strictfp",
    "super",
    "switch",
    "synchronized",
    "this",
    "throw",
    "throws",
    "to",
    "transient",
    "transitive",
    "true",
    "try",
    "uses",
    "var",
    "void",
    "volatile",
    "when",
    "while",
    "with",
    "yield",
}
_JAVA_PRIMITIVE_TYPES = {
    "boolean",
    "byte",
    "char",
    "double",
    "float",
    "int",
    "long",
    "short",
    "void",
}
_PYTHON_WILDCARD_BINDING = "*"


def _ecma_import_clause_is_safe(match: re.Match[str]) -> bool:
    if match.group(1):
        return True
    after_import = match.group(0).split("import", 1)[1]
    clause = re.split(r"[ \t]+from[ \t]+", after_import, maxsplit=1)[0]
    identifiers = re.findall(r"[A-Za-z_$][\w$]*", clause)
    return all(
        identifier == "as" or identifier not in _ECMA_RESERVED_IDENTIFIERS
        for identifier in identifiers
    )


def _ecma_simple_type_is_safe(identifier: str | None) -> bool:
    return (
        identifier is None
        or identifier not in _ECMA_RESERVED_IDENTIFIERS
        or identifier in _ECMA_ALLOWED_SIMPLE_TYPES
    )


def _java_identifier_path_is_safe(identifier: str | None) -> bool:
    if identifier is None:
        return True
    return all(part not in _JAVA_RESERVED_IDENTIFIERS for part in identifier.split("."))


def _java_import_path_is_safe(identifier: str) -> bool:
    path = identifier.removesuffix(".*")
    return _java_identifier_path_is_safe(path)


def _java_type_is_safe(identifier: str | None) -> bool:
    if identifier is None:
        return True
    base = identifier.split("<", 1)[0].removesuffix("[]")
    return base in _JAVA_PRIMITIVE_TYPES or _java_identifier_path_is_safe(base)


def _nesting_depths_at(content: str, positions: Iterable[int]) -> dict[int, int]:
    """Return conservative brace/parenthesis/bracket depth in one linear scan."""

    depths: dict[int, int] = {}
    cursor = 0
    depth = 0
    for position in sorted(set(positions)):
        while cursor < position:
            if content[cursor] in "{([":
                depth += 1
            elif content[cursor] in "})]":
                depth = max(0, depth - 1)
            cursor += 1
        depths[position] = depth
    return depths


def _line_numbers_at(content: str, positions: Iterable[int]) -> dict[int, int]:
    """Map sorted offsets to one-based lines without rescanning prior text."""

    lines: dict[int, int] = {}
    cursor = 0
    line = 1
    for position in sorted(set(positions)):
        line += content.count("\n", cursor, position)
        lines[position] = line
        cursor = position
    return lines


def _delimiters_are_balanced(content: str) -> bool:
    pairs = {"}": "{", ")": "(", "]": "["}
    stack: list[str] = []
    for character in content:
        if character in "{([":
            stack.append(character)
        elif character in pairs:
            if not stack or stack.pop() != pairs[character]:
                return False
    return not stack


def _has_statement_boundary(
    content: str,
    position: int,
    *,
    allowed_previous: str,
) -> bool:
    cursor = position - 1
    while cursor >= 0 and content[cursor].isspace():
        cursor -= 1
    return cursor < 0 or content[cursor] in allowed_previous


def _find_unescaped(content: str, marker: str, start: int) -> int:
    candidate = content.find(marker, start)
    while candidate >= 0:
        backslashes = 0
        cursor = candidate - 1
        while cursor >= 0 and content[cursor] == "\\":
            backslashes += 1
            cursor -= 1
        if backslashes % 2 == 0:
            return candidate
        candidate = content.find(marker, candidate + 1)
    return -1


def _ecma_has_ambiguous_regex_static_syntax(masked_code: str) -> bool:
    """Withhold facts when slash-delimited text can corrupt bounded parsing.

    Strings and comments are skipped. The remaining `/.../` pair may be a
    regular expression or division; if it contains nesting or static-syntax
    tokens, the adapter refuses the whole file rather than guessing.
    """

    index = 0
    length = len(masked_code)
    static_keyword = re.compile(r"\b(?:import|export|class|interface|function)\b")
    while index < length:
        if masked_code.startswith("//", index):
            newline = masked_code.find("\n", index + 2)
            index = length if newline < 0 else newline + 1
            continue
        if masked_code.startswith("/*", index):
            closing = masked_code.find("*/", index + 2)
            index = length if closing < 0 else closing + 2
            continue
        quote = masked_code[index]
        if quote in {"'", '"', "`"}:
            index += 1
            while index < length:
                if masked_code[index] == "\\":
                    index = min(length, index + 2)
                    continue
                if masked_code[index] == quote:
                    index += 1
                    break
                index += 1
            continue
        if quote != "/":
            index += 1
            continue
        closing = _find_unescaped(masked_code, "/", index + 1)
        newline = masked_code.find("\n", index + 1)
        if closing < 0 or (newline >= 0 and newline < closing):
            index += 1
            continue
        between = masked_code[index + 1 : closing]
        if any(marker in between for marker in "{}()[]") or static_keyword.search(between):
            return True
        index = closing + 1
    return False


def _mask_non_code(
    content: str,
    *,
    template_literals: bool,
    java_text_blocks: bool,
) -> _MaskedSource:
    """Mask comments and literals without changing offsets or line breaks.

    `comments_only` retains literal text so the ECMAScript import adapter can
    recover a real module specifier. Matches whose keyword starts inside one of
    the recorded literal spans are rejected.
    """

    code = list(content)
    comments_only = list(content)
    literal_spans: list[tuple[int, int]] = []
    length = len(content)

    def mask(buffer: list[str], start: int, end: int) -> None:
        for position in range(start, end):
            if buffer[position] not in {"\n", "\r"}:
                buffer[position] = " "

    index = 0
    while index < length:
        if content.startswith("//", index):
            end = content.find("\n", index + 2)
            end = length if end < 0 else end
            mask(code, index, end)
            mask(comments_only, index, end)
            index = end
            continue
        if content.startswith("/*", index):
            closing = content.find("*/", index + 2)
            end = length if closing < 0 else closing + 2
            mask(code, index, end)
            mask(comments_only, index, end)
            index = end
            continue
        if java_text_blocks and content.startswith('"""', index):
            closing = _find_unescaped(content, '"""', index + 3)
            end = length if closing < 0 else closing + 3
            literal_spans.append((index, end))
            mask(code, index, end)
            index = end
            continue
        quote = content[index]
        if quote in {"'", '"'} or (template_literals and quote == "`"):
            start = index
            index += 1
            while index < length:
                if content[index] == "\\":
                    index = min(length, index + 2)
                    continue
                if content[index] == quote:
                    index += 1
                    break
                index += 1
            literal_spans.append((start, index))
            mask(code, start, index)
            continue
        index += 1

    return _MaskedSource("".join(code), "".join(comments_only), tuple(literal_spans))


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
        if Path(relative_path).suffix.casefold() in {".jsx", ".tsx"}:
            return ParsedFile(
                path=relative_path,
                language=language,
                capabilities=(
                    LanguageCapability.FILE_LEVEL,
                    LanguageCapability.PARTIAL_ANALYSIS,
                ),
            )
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
        module_rebindings = _python_scope_bindings(tree.body)
        module_wildcard_import = _PYTHON_WILDCARD_BINDING in module_rebindings
        symbols_by_name: dict[str, list[CodeSymbol]] = {}
        symbols_by_qualified_name: dict[str, list[CodeSymbol]] = {}
        for symbol in visitor.symbols:
            symbols_by_name.setdefault(symbol.name, []).append(symbol)
            symbols_by_qualified_name.setdefault(symbol.qualified_name, []).append(symbol)

        def reference_is_confirmed(reference: _PythonReference) -> bool:
            if (
                reference.shadowed
                or module_wildcard_import
                or reference.target in module_rebindings
                or "." in reference.target
                or not reference.source_symbol
            ):
                return False
            targets = symbols_by_name.get(reference.target, [])
            sources = symbols_by_qualified_name.get(reference.source_symbol, [])
            if len(targets) != 1 or len(sources) != 1:
                return False
            target = targets[0]
            source = sources[0]
            if source.kind not in {SymbolKind.FUNCTION, SymbolKind.METHOD}:
                return False
            target_parent, _, _target_name = target.qualified_name.rpartition(".")
            if not target_parent:
                return True
            parent_symbols = symbols_by_qualified_name.get(target_parent, [])
            if len(parent_symbols) != 1:
                return False
            parent = parent_symbols[0]
            return parent.kind in {SymbolKind.FUNCTION, SymbolKind.METHOD} and (
                source.qualified_name == target_parent
                or source.qualified_name.startswith(f"{target_parent}.")
            )

        def relationship_is_confirmed(relation: _PythonTypeRelation) -> bool:
            if (
                relation.shadowed
                or module_wildcard_import
                or relation.target in module_rebindings
                or "." in relation.target
            ):
                return False
            targets = [
                symbol
                for symbol in symbols_by_name.get(relation.target, [])
                if symbol.kind in {SymbolKind.CLASS, SymbolKind.INTERFACE}
            ]
            if len(targets) != 1:
                return False
            target = targets[0]
            if target.start_line >= relation.line:
                return False
            source_parent, _, _source_name = relation.source_symbol.rpartition(".")
            target_parent, _, _target_name = target.qualified_name.rpartition(".")
            if not target_parent:
                return True
            parent_symbols = symbols_by_qualified_name.get(target_parent, [])
            if len(parent_symbols) != 1:
                return False
            parent = parent_symbols[0]
            if parent.kind in {SymbolKind.FUNCTION, SymbolKind.METHOD}:
                return source_parent == target_parent or source_parent.startswith(
                    f"{target_parent}."
                )
            return parent.kind == SymbolKind.CLASS and source_parent == target_parent

        references = tuple(
            CodeReference(
                reference.source_symbol,
                reference.target,
                reference.kind,
                reference.line,
                resolved=reference_is_confirmed(reference),
                status=(
                    RelationStatus.CONFIRMED
                    if reference_is_confirmed(reference)
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
                    if relationship_is_confirmed(relation)
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
        if _ECMA_HTML_COMMENT.search(content) or _ecma_has_ambiguous_regex_static_syntax(
            content
        ):
            return ParsedFile(
                path=path,
                language=language,
                capabilities=(
                    LanguageCapability.FILE_LEVEL,
                    LanguageCapability.PARTIAL_ANALYSIS,
                ),
            )
        masked = _mask_non_code(content, template_literals=True, java_text_blocks=False)
        if not _delimiters_are_balanced(masked.code):
            return ParsedFile(
                path=path,
                language=language,
                capabilities=(
                    LanguageCapability.FILE_LEVEL,
                    LanguageCapability.PARTIAL_ANALYSIS,
                ),
            )
        import_matches = list(_ECMA_IMPORT.finditer(masked.comments_only))
        import_depths = _nesting_depths_at(
            masked.code,
            (match.start() for match in import_matches),
        )
        imports = tuple(
            sorted(
                {
                    match.group(1) or match.group(2)
                    for match in import_matches
                    if not masked.position_is_literal(match.start())
                    and import_depths[match.start()] == 0
                    and _has_statement_boundary(
                        masked.code,
                        match.start(),
                        allowed_previous=";}",
                    )
                    and _ecma_import_clause_is_safe(match)
                }
            )
        )
        symbols: list[CodeSymbol] = []
        exports: set[str] = set()
        symbol_matches = list(_ECMA_SYMBOL.finditer(masked.code))
        symbol_depths = _nesting_depths_at(
            masked.code,
            (match.start() for match in symbol_matches),
        )
        symbol_lines = _line_numbers_at(
            content,
            (match.start() for match in symbol_matches),
        )
        for match in symbol_matches:
            if symbol_depths[match.start()] != 0 or not _has_statement_boundary(
                masked.code,
                match.start(),
                allowed_previous=";}",
            ):
                continue
            (
                type_declaration,
                type_name,
                parent,
                implementations,
                function_declaration,
                function_name,
                function_parameter,
                function_parameter_type,
                function_return_type,
                arrow,
                arrow_parameter,
                arrow_parameter_type,
            ) = match.groups()
            declaration = type_declaration or function_declaration
            name = type_name or function_name or arrow
            signature = content[match.start() : match.end()].strip()
            identifier_fields = (
                name,
                parent,
                function_parameter,
                arrow_parameter,
                *((implementations or "").split(",")),
            )
            if (
                any(
                    identifier and identifier.strip() in _ECMA_RESERVED_IDENTIFIERS
                    for identifier in identifier_fields
                )
                or not all(
                    _ecma_simple_type_is_safe(identifier)
                    for identifier in (
                        function_parameter_type,
                        function_return_type,
                        arrow_parameter_type,
                    )
                )
                or (
                    declaration == "interface"
                    and " implements " in f" {signature} "
                )
            ) or (
                language == "javascript"
                and (
                    declaration == "interface"
                    or " implements " in f" {signature} "
                    or ":" in signature
                )
            ):
                continue
            if declaration == "class":
                kind = SymbolKind.CLASS
            elif declaration == "interface":
                kind = SymbolKind.INTERFACE
            else:
                kind = SymbolKind.FUNCTION
            line = symbol_lines[match.start()]
            symbols.append(CodeSymbol(name, name, kind, signature, line, line))
            if signature.startswith("export "):
                exports.add(name)
        export_matches = list(_ECMA_NAMED_EXPORT.finditer(masked.code))
        export_depths = _nesting_depths_at(
            masked.code,
            (match.start() for match in export_matches),
        )
        for match in export_matches:
            if export_depths[match.start()] != 0 or not _has_statement_boundary(
                masked.code,
                match.start(),
                allowed_previous=";}",
            ):
                continue
            for item in match.group(1).split(","):
                identifiers = item.strip().split(" as ")
                if any(
                    identifier in _ECMA_RESERVED_IDENTIFIERS
                    for identifier in identifiers
                ):
                    continue
                exported = identifiers[-1].strip()
                if exported:
                    exports.add(exported)
        relationships: list[TypeRelation] = []
        relation_matches = list(_ECMA_TYPE_RELATION.finditer(masked.code))
        relation_depths = _nesting_depths_at(
            masked.code,
            (match.start() for match in relation_matches),
        )
        relation_lines = _line_numbers_at(
            content,
            (match.start() for match in relation_matches),
        )
        for match in relation_matches:
            if relation_depths[match.start()] != 0 or not _has_statement_boundary(
                masked.code,
                match.start(),
                allowed_previous=";}",
            ):
                continue
            relation_kind, source, parent, implementations = match.groups()
            if (
                any(
                    identifier.strip() in _ECMA_RESERVED_IDENTIFIERS
                    for identifier in (
                        source,
                        parent or "",
                        *((implementations or "").split(",")),
                    )
                    if identifier.strip()
                )
                or (relation_kind == "interface" and implementations)
            ) or (
                language == "javascript"
                and (relation_kind == "interface" or implementations)
            ):
                continue
            line = relation_lines[match.start()]
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
        if _JAVA_UNICODE_ESCAPE.search(content):
            return ParsedFile(
                path=path,
                language="java",
                capabilities=(
                    LanguageCapability.FILE_LEVEL,
                    LanguageCapability.PARTIAL_ANALYSIS,
                ),
            )
        masked = _mask_non_code(content, template_literals=False, java_text_blocks=True)
        if not _delimiters_are_balanced(masked.code):
            return ParsedFile(
                path=path,
                language="java",
                capabilities=(
                    LanguageCapability.FILE_LEVEL,
                    LanguageCapability.PARTIAL_ANALYSIS,
                ),
            )
        imports = tuple(
            sorted(
                {
                    imported
                    for imported in _JAVA_IMPORT.findall(masked.code)
                    if _java_import_path_is_safe(imported)
                }
            )
        )
        symbols: list[CodeSymbol] = []
        type_matches = list(_JAVA_TYPE.finditer(masked.code))
        type_depths = _nesting_depths_at(
            masked.code,
            (match.start() for match in type_matches),
        )
        type_lines = _line_numbers_at(
            content,
            (match.start() for match in type_matches),
        )
        for match in type_matches:
            if type_depths[match.start()] != 0 or not _has_statement_boundary(
                masked.code,
                match.start(),
                allowed_previous=";}",
            ):
                continue
            declaration_kind, name, parent, implementations = match.groups()
            kind = (
                SymbolKind.CLASS
                if declaration_kind == "class"
                else SymbolKind.INTERFACE
            )
            line = type_lines[match.start()]
            signature = content[match.start() : match.end()].strip()
            if (
                name in _JAVA_RESERVED_IDENTIFIERS
                or not _java_identifier_path_is_safe(parent)
                or not all(
                    _java_identifier_path_is_safe(identifier.strip())
                    for identifier in (implementations or "").split(",")
                    if identifier.strip()
                )
                or (kind == SymbolKind.INTERFACE and implementations)
            ):
                continue
            symbols.append(
                CodeSymbol(name, name, kind, signature, line, line)
            )
        method_matches = list(_JAVA_METHOD.finditer(masked.code))
        method_depths = _nesting_depths_at(
            masked.code,
            (match.start() for match in method_matches),
        )
        method_lines = _line_numbers_at(
            content,
            (match.start() for match in method_matches),
        )
        for match in method_matches:
            signature = content[match.start() : match.end()].strip()
            first_token = signature.split(maxsplit=1)[0]
            return_type, method_name, parameter_type, parameter_name, throws_types = (
                match.groups()
            )
            if (
                method_depths[match.start()] != 1
                or not _has_statement_boundary(
                    masked.code,
                    match.start(),
                    allowed_previous="{;}",
                )
                or first_token in _JAVA_NON_METHOD_PREFIXES
                or not _java_type_is_safe(return_type)
                or method_name in _JAVA_RESERVED_IDENTIFIERS
                or not _java_type_is_safe(parameter_type)
                or (
                    parameter_name is not None
                    and parameter_name in _JAVA_RESERVED_IDENTIFIERS
                )
                or not all(
                    _java_identifier_path_is_safe(identifier.strip())
                    for identifier in (throws_types or "").split(",")
                    if identifier.strip()
                )
                or "=" in signature
                or "->" in signature
            ):
                continue
            line = method_lines[match.start()]
            symbols.append(
                CodeSymbol(
                    match.group(2),
                    match.group(2),
                    SymbolKind.METHOD,
                    signature,
                    line,
                    line,
                )
            )
        relationships: list[TypeRelation] = []
        relation_matches = list(_JAVA_TYPE_RELATION.finditer(masked.code))
        relation_depths = _nesting_depths_at(
            masked.code,
            (match.start() for match in relation_matches),
        )
        relation_lines = _line_numbers_at(
            content,
            (match.start() for match in relation_matches),
        )
        for match in relation_matches:
            if relation_depths[match.start()] != 0 or not _has_statement_boundary(
                masked.code,
                match.start(),
                allowed_previous=";}",
            ):
                continue
            relation_kind, source, parent, implementations = match.groups()
            if (
                source in _JAVA_RESERVED_IDENTIFIERS
                or not _java_identifier_path_is_safe(parent)
                or not all(
                    _java_identifier_path_is_safe(identifier.strip())
                    for identifier in (implementations or "").split(",")
                    if identifier.strip()
                )
                or (relation_kind == "interface" and implementations)
            ):
                continue
            line = relation_lines[match.start()]
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


class _PythonFunctionBindingCollector(ast.NodeVisitor):
    """Collect bindings in one function without crossing nested semantic scopes."""

    def __init__(self) -> None:
        self.bindings: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.bindings.add(node.id)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.bindings.add(alias.asname or alias.name.split(".", 1)[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self.bindings.add(
                _PYTHON_WILDCARD_BINDING
                if alias.name == "*"
                else alias.asname or alias.name
            )

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self.bindings.add(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            self.bindings.add(node.name)
        self.generic_visit(node)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        if node.name:
            self.bindings.add(node.name)

    def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
        if node.rest:
            self.bindings.add(node.rest)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default is not None:
                self.visit(default)
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ):
            if argument.annotation is not None:
                self.visit(argument.annotation)
        if node.args.vararg and node.args.vararg.annotation is not None:
            self.visit(node.args.vararg.annotation)
        if node.args.kwarg and node.args.kwarg.annotation is not None:
            self.visit(node.args.kwarg.annotation)
        if node.returns is not None:
            self.visit(node.returns)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default is not None:
                self.visit(default)


def _python_scope_bindings(statements: Iterable[ast.stmt]) -> frozenset[str]:
    collector = _PythonFunctionBindingCollector()
    for statement in statements:
        collector.visit(statement)
    return frozenset(collector.bindings)


def _python_function_bindings(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> frozenset[str]:
    bindings = {
        argument.arg
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
    }
    if node.args.vararg:
        bindings.add(node.args.vararg.arg)
    if node.args.kwarg:
        bindings.add(node.args.kwarg.arg)
    bindings.update(_python_scope_bindings(node.body))
    return frozenset(bindings)


def _python_lambda_bindings(node: ast.Lambda) -> frozenset[str]:
    bindings = {
        argument.arg
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
    }
    if node.args.vararg:
        bindings.add(node.args.vararg.arg)
    if node.args.kwarg:
        bindings.add(node.args.kwarg.arg)
    collector = _PythonFunctionBindingCollector()
    collector.visit(node.body)
    bindings.update(collector.bindings)
    return frozenset(bindings)


@dataclass
class _PythonVisitor(ast.NodeVisitor):
    imports: set[str] = field(default_factory=set)
    symbols: list[CodeSymbol] = field(default_factory=list)
    references: list[_PythonReference] = field(default_factory=list)
    relationships: list[_PythonTypeRelation] = field(default_factory=list)
    scope: list[str] = field(default_factory=list)
    scope_kinds: list[str] = field(default_factory=list)
    function_bindings: list[frozenset[str]] = field(default_factory=list)
    class_bindings: list[frozenset[str]] = field(default_factory=list)

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
                shadowed = "." not in target and (
                    any(
                        target in bindings or _PYTHON_WILDCARD_BINDING in bindings
                        for bindings in self.function_bindings
                    )
                    or any(
                        target in bindings or _PYTHON_WILDCARD_BINDING in bindings
                        for bindings in self.class_bindings
                    )
                )
                self.relationships.append(
                    _PythonTypeRelation(
                        source,
                        target,
                        "inherit",
                        node.lineno,
                        shadowed,
                    )
                )
        self.scope.append(node.name)
        self.scope_kinds.append("class")
        self.class_bindings.append(_python_scope_bindings(node.body))
        for statement in node.body:
            self.visit(statement)
        self.class_bindings.pop()
        self.scope_kinds.pop()
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        kind = (
            SymbolKind.METHOD
            if self.scope_kinds and self.scope_kinds[-1] == "class"
            else SymbolKind.FUNCTION
        )
        arguments = [
            argument.arg
            for argument in (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            )
        ]
        if node.args.vararg:
            arguments.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            arguments.append(f"**{node.args.kwarg.arg}")
        self._record_symbol(node, kind, f"{node.name}({', '.join(arguments)})")
        self.scope.append(node.name)
        self.scope_kinds.append("function")
        self.function_bindings.append(_python_function_bindings(node))
        for statement in node.body:
            self.visit(statement)
        self.function_bindings.pop()
        self.scope_kinds.pop()
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self.function_bindings.append(_python_lambda_bindings(node))
        self.visit(node.body)
        self.function_bindings.pop()

    def visit_Call(self, node: ast.Call) -> None:
        target = self._call_name(node.func)
        if target:
            shadowed = "." not in target and any(
                target in bindings or _PYTHON_WILDCARD_BINDING in bindings
                for bindings in reversed(self.function_bindings)
            )
            self.references.append(
                _PythonReference(
                    ".".join(self.scope) or None,
                    target,
                    "call",
                    node.lineno,
                    shadowed,
                )
            )
        self.generic_visit(node)

    def _record_symbol(
        self,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        kind: SymbolKind,
        signature: str,
    ) -> None:
        qualified = ".".join([*self.scope, node.name])
        decorator_lines = [decorator.lineno for decorator in node.decorator_list]
        self.symbols.append(
            CodeSymbol(
                node.name,
                qualified,
                kind,
                signature,
                min([node.lineno, *decorator_lines]),
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
