"""Read CSS the way a browser does: comments and strings are not code.

Stdlib only: build.py runs on a system python3.
"""

from __future__ import annotations

from typing import NamedTuple


class BuildError(RuntimeError):
    pass


def code_mask(css: str, strings: bool = False) -> list[bool]:
    """True for each character that is CSS code; False inside comments and, unless strings is
    set, inside strings."""
    mask = [True] * len(css)
    i, n = 0, len(css)
    while i < n:
        if css.startswith("/*", i):
            end = css.find("*/", i + 2)
            end = n if end == -1 else end + 2
        elif css[i] in "\"'":
            quote, end = css[i], i + 1
            while end < n and css[end] not in (quote, "\n"):
                end += 2 if css[end] == "\\" else 1
            # A string left open ends at its newline, as in a browser.
            end = end + 1 if end < n and css[end] == quote else min(end, n)
            if strings:
                i = end
                continue
        else:
            i += 1
            continue
        for j in range(i, end):
            mask[j] = False
        i = end
    return mask


class BraceScan(NamedTuple):
    open: int  # blocks still open at end of input
    strays: list[int]  # offsets of top-level } that close nothing


def brace_scan(css: str) -> BraceScan:
    """Brace structure as a browser sees it, ignoring comments and strings.

    A } at top level closes nothing: the browser reports a parse error and
    the stray token swallows the rule that follows it. It never cancels a
    later {, so the running depth is floored at zero.
    """
    depth, strays = 0, []
    for i, (ch, is_code) in enumerate(zip(css, code_mask(css))):
        if not is_code:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            if depth:
                depth -= 1
            else:
                strays.append(i)
    return BraceScan(depth, strays)


def line_of(css: str, offset: int) -> int:
    return css.count("\n", 0, offset) + 1


def split_imports(css: str) -> tuple[list[str], str]:
    """Pull every top-level @import statement out of css, in order."""
    css = css.replace("\r\n", "\n")
    mask = code_mask(css)
    imports: list[str] = []
    keep: list[str] = []
    depth = last = i = 0
    n = len(css)
    while i < n:
        if mask[i]:
            ch = css[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif ch == "@" and css.startswith("@import", i):
                if depth != 0:
                    raise BuildError(f"@import inside a block at offset {i}")
                j = i
                while j < n and not (css[j] == ";" and mask[j]):
                    j += 1
                if j == n:
                    raise BuildError(f"unterminated @import at offset {i}")
                imports.append(css[i : j + 1])
                keep.append(css[last:i])
                last = i = j + 1
                continue
        i += 1
    keep.append(css[last:])
    return imports, "".join(keep)


def _code_only(text: str) -> str:
    return "".join(c if m else " " for c, m in zip(text, code_mask(text)))


class Rule(NamedTuple):
    prelude: str  # selector list or at-rule prelude, whitespace-normalised
    body: str  # the text between the braces
    offset: int  # offset of the opening brace
    context: tuple[str, ...]  # enclosing at-rule preludes, outermost first


def leaf_rules(css: str) -> list[Rule]:
    """Every block that holds declarations, with the at-rule preludes around it. A rule that
    nests others keeps only its own declarations, the nested rules cut out of its body."""
    code = _code_only(css)
    stack: list[list] = []  # [prelude, open offset, prelude start, spans of nested rules]
    rules: list[Rule] = []
    start = 0
    for i, ch in enumerate(code):
        if ch == "{":
            stack.append([" ".join(code[start:i].split()), i, start, []])
            start = i + 1
        elif ch == "}":
            if stack:
                prelude, at, began, nested = stack.pop()
                if stack:
                    stack[-1][3].append((began, i + 1))
                body, cut = "", at + 1
                for a, b in nested:
                    body, cut = body + css[cut:a], b
                body += css[cut:i]
                if not nested or body.strip():
                    rules.append(Rule(prelude, body, at, tuple(s[0] for s in stack)))
            start = i + 1
        elif ch == ";":
            start = i + 1
    return rules


def declarations(body: str, keep_strings: bool = False) -> list[tuple[str, str]]:
    """(property, value) pairs of a declaration block, in order, comments removed. Strings
    are blanked unless keep_strings is set."""
    code = _code_only(body)
    kept = "".join(c if m else " " for c, m in zip(body, code_mask(body, strings=True))) if keep_strings else code
    out: list[tuple[str, str]] = []
    depth = start = 0
    for i, ch in enumerate(code + ";"):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == ";" and depth == 0:
            text, start = kept[start:i], i + 1
            if ":" in text:
                prop, value = text.split(":", 1)
                out.append((prop.strip().lower(), " ".join(value.split())))
    return out


def selectors(prelude: str) -> list[str]:
    """A selector list split on its top-level commas."""
    out: list[str] = []
    depth = start = 0
    for i, ch in enumerate(prelude + ","):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and depth == 0:
            part = " ".join(prelude[start:i].split())
            if part:
                out.append(part)
            start = i + 1
    return out


def _name_char(ch: str) -> bool:
    return ch.isalnum() or ch in "-_" or ord(ch) > 127


def strip_comments(css: str) -> str:
    """css without comments, blank lines or trailing spaces: what the browser reads, smaller.
    Strings are kept whole. A comment that alone separates two name characters (1px/**/solid)
    would join two tokens once removed, so it is an error rather than a silent change."""
    mask = code_mask(css, strings=True)
    out: list[str] = []
    i, n = 0, len(css)
    while i < n:
        if mask[i]:
            out.append(css[i])
            i += 1
            continue
        start = i
        while i < n and not mask[i]:
            i += 1
        before, after = css[start - 1 : start], css[i : i + 1]
        if before and after and _name_char(before) and _name_char(after):
            raise BuildError(f"line {line_of(css, start)}: a comment is all that separates {before!r} from {after!r}; add a space")
    lines = (line.rstrip() for line in "".join(out).split("\n"))
    return "\n".join(line for line in lines if line) + "\n"
