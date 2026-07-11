"""Commit-bound code parsing and incremental indexing."""

from .changes import changed_line_numbers, changed_symbols
from .indexer import IndexSnapshot, RepositoryIndexer
from .parser import (
    PARSER_CAPABILITY_MATRIX,
    CapabilityAssessment,
    CapabilityStatus,
    CodeReference,
    CodeSymbol,
    LanguageCapability,
    ParsedFile,
    ParserFeature,
    RelationStatus,
    SymbolKind,
    TypeRelation,
    UnifiedCodeParser,
    map_changed_symbols,
)

__all__ = [
    "PARSER_CAPABILITY_MATRIX",
    "CapabilityAssessment",
    "CapabilityStatus",
    "CodeReference",
    "CodeSymbol",
    "IndexSnapshot",
    "LanguageCapability",
    "ParsedFile",
    "ParserFeature",
    "RelationStatus",
    "SymbolKind",
    "RepositoryIndexer",
    "UnifiedCodeParser",
    "TypeRelation",
    "changed_line_numbers",
    "changed_symbols",
    "map_changed_symbols",
]
