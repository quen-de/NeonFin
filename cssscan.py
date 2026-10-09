"""Read CSS the way a browser does: comments and strings are not code.

Stdlib only: build.py runs on a system python3.
"""

from __future__ import annotations

from typing import NamedTuple


class BuildError(RuntimeError):
    pass


def code_mask(css: str) -> list[bool]:
    """True for each character that is CSS code; False inside comments and strings."""
    mask = [True] * len(css)
    i, n = 0, len(css)
    while i < n:
        if css.startswith("/*", i):
            end = css.find("*/", i + 2)
            end = n if end == -1 else end + 2
        elif css[i] in "\"'":
            quote, end = css[i], i + 1
            while end < n and css[end] != quote:
                end += 2 if css[end] == "\\" else 1
            end = min(end + 1, n)
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
    """Every block that holds declarations, with the at-rule preludes around it."""
    code = _code_only(css)
    stack: list[list] = []  # [prelude, open offset, holds a nested block]
    rules: list[Rule] = []
    start = 0
    for i, ch in enumerate(code):
        if ch == "{":
            if stack:
                stack[-1][2] = True
            stack.append([" ".join(code[start:i].split()), i, False])
            start = i + 1
        elif ch == "}":
            if stack:
                prelude, at, nested = stack.pop()
                if not nested:
                    rules.append(Rule(prelude, css[at + 1 : i], at, tuple(s[0] for s in stack)))
            start = i + 1
        elif ch == ";":
            start = i + 1
    return rules


def declarations(body: str) -> list[tuple[str, str]]:
    """(property, value) pairs of a declaration block, in order, comments removed."""
    code = _code_only(body)
    out: list[tuple[str, str]] = []
    depth = start = 0
    for i, ch in enumerate(code + ";"):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == ";" and depth == 0:
            text, start = code[start:i], i + 1
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
