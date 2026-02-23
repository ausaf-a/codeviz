"""Syntax tokenization using Pygments."""

from pathlib import Path
from pygments import lex
from pygments.lexers import get_lexer_for_filename, get_lexer_by_name, TextLexer
from pygments.token import Token


# Map file extensions to language names for cases where Pygments needs help
EXTENSION_TO_LANGUAGE = {
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".svelte": "html",
    ".vue": "html",
}

# Map Pygments token types to simplified categories for coloring
TOKEN_CATEGORIES = {
    Token.Keyword: "keyword",
    Token.Keyword.Constant: "keyword",
    Token.Keyword.Declaration: "keyword",
    Token.Keyword.Namespace: "keyword",
    Token.Keyword.Pseudo: "keyword",
    Token.Keyword.Reserved: "keyword",
    Token.Keyword.Type: "keyword_type",

    Token.Name.Function: "function",
    Token.Name.Function.Magic: "function",
    Token.Name.Class: "class",
    Token.Name.Decorator: "decorator",
    Token.Name.Builtin: "builtin",
    Token.Name.Builtin.Pseudo: "builtin",

    Token.String: "string",
    Token.String.Affix: "string",
    Token.String.Backtick: "string",
    Token.String.Char: "string",
    Token.String.Delimiter: "string",
    Token.String.Doc: "string",
    Token.String.Double: "string",
    Token.String.Escape: "string_escape",
    Token.String.Heredoc: "string",
    Token.String.Interpol: "string_interpol",
    Token.String.Other: "string",
    Token.String.Regex: "regex",
    Token.String.Single: "string",
    Token.String.Symbol: "string",

    Token.Number: "number",
    Token.Number.Bin: "number",
    Token.Number.Float: "number",
    Token.Number.Hex: "number",
    Token.Number.Integer: "number",
    Token.Number.Integer.Long: "number",
    Token.Number.Oct: "number",

    Token.Operator: "operator",
    Token.Operator.Word: "operator",
    Token.Punctuation: "punctuation",

    Token.Comment: "comment",
    Token.Comment.Hashbang: "comment",
    Token.Comment.Multiline: "comment",
    Token.Comment.Preproc: "preprocessor",
    Token.Comment.PreprocFile: "preprocessor",
    Token.Comment.Single: "comment",
    Token.Comment.Special: "comment",

    Token.Name.Namespace: "namespace",
    Token.Name.Variable: "variable",
    Token.Name.Variable.Class: "variable",
    Token.Name.Variable.Global: "variable",
    Token.Name.Variable.Instance: "variable",
    Token.Name.Variable.Magic: "variable",
    Token.Name.Attribute: "attribute",
    Token.Name.Tag: "tag",

    Token.Literal: "literal",
    Token.Generic: "text",
    Token.Text: "text",
    Token.Text.Whitespace: "whitespace",
}


def get_language_for_file(filename: str) -> str:
    """Get the language name for a filename."""
    ext = Path(filename).suffix.lower()
    if ext in EXTENSION_TO_LANGUAGE:
        return EXTENSION_TO_LANGUAGE[ext]

    try:
        lexer = get_lexer_for_filename(filename)
        return lexer.name.lower()
    except Exception:
        return "text"


def get_token_category(token_type) -> str:
    """Map a Pygments token type to a simplified category."""
    # Walk up the token type hierarchy to find a match
    while token_type:
        if token_type in TOKEN_CATEGORIES:
            return TOKEN_CATEGORIES[token_type]
        token_type = token_type.parent
    return "text"


def tokenize_file(content: str, filename: str) -> list[dict]:
    """
    Tokenize file content with syntax highlighting info.

    Args:
        content: File content string
        filename: Filename (used to detect language)

    Returns:
        List of token dicts with keys: type, value, category
    """
    # Get appropriate lexer
    ext = Path(filename).suffix.lower()
    try:
        if ext in EXTENSION_TO_LANGUAGE:
            lexer = get_lexer_by_name(EXTENSION_TO_LANGUAGE[ext])
        else:
            lexer = get_lexer_for_filename(filename)
    except Exception:
        lexer = TextLexer()

    tokens = []
    for token_type, value in lex(content, lexer):
        if not value:
            continue

        category = get_token_category(token_type)
        tokens.append({
            "type": str(token_type),
            "value": value,
            "category": category,
        })

    return tokens


def tokenize_to_lines(content: str, filename: str) -> list[list[dict]]:
    """
    Tokenize file content and organize by lines.

    Args:
        content: File content string
        filename: Filename (used to detect language)

    Returns:
        List of lines, where each line is a list of token dicts
    """
    tokens = tokenize_file(content, filename)

    lines = [[]]
    for token in tokens:
        value = token["value"]
        category = token["category"]

        # Split token by newlines
        parts = value.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                lines.append([])
            if part:
                lines[-1].append({
                    "value": part,
                    "category": category,
                })

    return lines
