import re
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from triad import (
    NAME_FLAT,
    NAME_SHARP,
    PC_TO_FLAT,
    PC_TO_SHARP,
    Triad,
)

UTT = Tuple[int, int, int]


class NRT:
    """Encapsulates neo-Riemannian transformations using UTT normalization."""

    IDENTITY_UTT: UTT = (1, 0, 0)
    FLAT_ROOTS = {1, 3, 8, 10}
    NOTE_RE = r'[A-Ga-g](?:[#b♯♭])?'
    CANDIDATE_RE = re.compile(
        rf'''
        \(\s*{NOTE_RE}\s*,\s*[+\-Mm]\s*\) |
        [\[\{{]\s*{NOTE_RE}\s*,\s*{NOTE_RE}\s*,\s*{NOTE_RE}\s*[\]\}}] |
        \(\s*{NOTE_RE}(?:[+\-Mm]|min|minor)?\s*\) |
        {NOTE_RE}(?:[+\-Mm]|min|minor)?
        ''',
        re.VERBOSE,
    )

    BASE_UTT_TABLE: Dict[str, UTT] = {
        'P': (-1, 0, 0),
        'L': (-1, 4, 8),
        'R': (-1, 9, 3),
        'N': (-1, 5, 7),
        'H': (-1, 8, 4),
        'S': (-1, 1, 11),
    }

    COMPOUND_EXPANSION = {
        'H': ['P', 'L', 'P'],
        'N': ['P', 'L', 'R'],
        'S': ['L', 'P', 'R'],
        "P'": ['R', 'P', 'L'],
        "L'": ['R', 'L', 'P'],
        "R'": ['L', 'R', 'P'],
    }
    SUPERSCRIPT_TO_DIGIT = {
        '⁰': '0',
        '¹': '1',
        '²': '2',
        '³': '3',
        '⁴': '4',
        '⁵': '5',
        '⁶': '6',
        '⁷': '7',
        '⁸': '8',
        '⁹': '9',
    }

    def __init__(
        self,
        mode: str = 'lr',
        output_style: str = 'input',
        spelling: str = 'input',
        show_description: bool = False,
    ) -> None:
        if mode not in ('lr', 'rl'):
            raise ValueError("mode must be 'lr' or 'rl'")
        if output_style not in ('input', 'short', 'tuple', 'spell'):
            raise ValueError("output_style must be input|short|tuple|spell")
        if spelling not in ('input', 'sharp', 'flat', 'auto'):
            raise ValueError("spelling must be input|sharp|flat|auto")
        self.mode = mode
        self.output_style = output_style
        self.spelling = spelling
        self.show_description = show_description
        self.utt_table = dict(self.BASE_UTT_TABLE)
        self.utt_table["P'"] = self._obverse('R', 'P', 'L')
        self.utt_table["L'"] = self._obverse('R', 'L', 'P')
        self.utt_table["R'"] = self._obverse('L', 'R', 'P')

    @staticmethod
    def _mode_int(mode: str) -> int:
        return 1 if mode == '+' else -1

    @staticmethod
    def _mode_str(mode: int) -> str:
        return '+' if mode == 1 else '-'

    @staticmethod
    def _notes_of(root: int, mode: int) -> List[int]:
        third = 4 if mode == 1 else 3
        return [root % 12, (root + third) % 12, (root + 7) % 12]

    @classmethod
    def compose_utt(cls, u2: UTT, u1: UTT) -> UTT:
        """Return the UTT equivalent to applying u1 first, then u2."""
        s1, tp, tm = u1
        s2, up, um = u2
        if s1 == 1:
            add_p, add_m = up, um
        else:
            add_p, add_m = um, up
        return (s1 * s2, (tp + add_p) % 12, (tm + add_m) % 12)

    def _obverse(self, a: str, b: str, c: str) -> UTT:
        u = self.IDENTITY_UTT
        for name in (a, b, c):
            u = self.compose_utt(self.utt_table[name], u)
        return u

    @staticmethod
    def _parse_sigma(token: str) -> int:
        token = token.strip()
        if token in ('+', '+1', '1'):
            return 1
        if token in ('-', '-1'):
            return -1
        raise ValueError(f"invalid sigma in UTT: {token!r}")

    def parse_utt_literal(self, text: str) -> UTT:
        m = re.fullmatch(r'<\s*([^,]+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*>', text.strip())
        if not m:
            raise ValueError(f"cannot parse UTT: {text!r}")
        sigma = self._parse_sigma(m.group(1))
        return (sigma, int(m.group(2)) % 12, int(m.group(3)) % 12)

    def token_to_utt(self, token: str) -> UTT:
        if token in self.utt_table:
            return self.utt_table[token]
        m = re.fullmatch(r'T(-?\d+)', token)
        if m:
            n = int(m.group(1)) % 12
            return (1, n, n)
        m = re.fullmatch(r'D(-?\d+)', token)
        if m:
            n = (5 * int(m.group(1))) % 12
            return (1, n, n)
        m = re.fullmatch(r'S(-?\d+)', token)
        if m:
            n = int(m.group(1)) % 12
            return (1, n, (-n) % 12)
        m = re.fullmatch(r'W(-?\d+)', token)
        if m:
            n = int(m.group(1)) % 12
            return (-1, (-n) % 12, n)
        m = re.fullmatch(r'I(-?\d+)?', token)
        if m:
            n = 0 if m.group(1) is None else int(m.group(1)) % 12
            return (-1, n, n)
        if token.startswith('<'):
            return self.parse_utt_literal(token)
        raise ValueError(f"unknown operator: {token!r}")

    def expand_group(self, group: str) -> List[str]:
        tokens: List[str] = []
        i = 0
        n = len(group)
        while i < n:
            c = group[i]
            if c in 'PLR':
                if i + 1 < n and group[i + 1] == "'":
                    tokens.append(group[i:i + 2])
                    i += 2
                else:
                    tokens.append(c)
                    i += 1
            elif c in 'NH':
                tokens.append(c)
                i += 1
            elif c in 'TDSWI':
                j = i + 1
                if j < n and group[j] == '-':
                    j += 1
                while j < n and group[j].isdigit():
                    j += 1
                if j == i + 1:
                    if c in ('S', 'I'):
                        tokens.append(c)
                        i = j
                        continue
                    raise ValueError(f"operator {c!r} requires a number")
                tokens.append(group[i:j])
                i = j
            elif c == '<':
                j = group.find('>', i)
                if j == -1:
                    raise ValueError("unterminated UTT literal '<...>'")
                tokens.append(group[i:j + 1])
                i = j + 1
            elif c.isspace():
                i += 1
            else:
                raise ValueError(f"unexpected character in operators: {c!r}")
        return tokens

    def _parse_exponent(self, text: str, i: int) -> Tuple[int, int]:
        if i >= len(text):
            return 1, i
        if text[i] == '^':
            j = i + 1
            if j >= len(text) or not text[j].isdigit():
                raise ValueError("expected digits after '^' in exponent")
            while j < len(text) and text[j].isdigit():
                j += 1
            return int(text[i + 1:j]), j
        if text[i] in self.SUPERSCRIPT_TO_DIGIT:
            j = i
            digits: List[str] = []
            while j < len(text) and text[j] in self.SUPERSCRIPT_TO_DIGIT:
                digits.append(self.SUPERSCRIPT_TO_DIGIT[text[j]])
                j += 1
            return int(''.join(digits)), j
        return 1, i

    def _read_atomic_token(self, text: str, i: int) -> Tuple[str, int]:
        c = text[i]
        if c in 'PLR':
            if i + 1 < len(text) and text[i + 1] == "'":
                return text[i:i + 2], i + 2
            return c, i + 1
        if c in 'NH':
            return c, i + 1
        if c in 'TDSWI':
            j = i + 1
            if j < len(text) and text[j] == '-':
                j += 1
            while j < len(text) and text[j].isdigit():
                j += 1
            if j == i + 1 and c not in ('S', 'I'):
                raise ValueError(f"operator {c!r} requires a number")
            return text[i:j], j
        if c == '<':
            j = text.find('>', i)
            if j == -1:
                raise ValueError("unterminated UTT literal '<...>'")
            return text[i:j + 1], j + 1
        raise ValueError(f"unexpected character in operators: {c!r}")

    def _expand_ops_text(self, text: str) -> str:
        compact = text.replace(' ', '')

        def parse_seq(i: int, stop: Optional[str] = None) -> Tuple[str, int]:
            out: List[str] = []
            n = len(compact)
            while i < n:
                c = compact[i]
                if stop is not None and c == stop:
                    return ''.join(out), i + 1
                if c == ')':
                    raise ValueError("unmatched ')' in operators")
                if c == '(':
                    inner, i = parse_seq(i + 1, ')')
                    exp, i = self._parse_exponent(compact, i)
                    out.append(inner * exp)
                    continue
                token, i = self._read_atomic_token(compact, i)
                exp, i = self._parse_exponent(compact, i)
                out.extend([token] * exp)
            if stop is not None:
                raise ValueError("unmatched '(' in operators")
            return ''.join(out), i

        expanded, pos = parse_seq(0, None)
        if pos != len(compact):
            raise ValueError("could not parse operator text")
        return expanded

    def _groups_from_text(self, text: str) -> List[str]:
        expanded = self._expand_ops_text(text)
        return [expanded] if expanded else []

    def group_to_utt(self, group: str) -> UTT:
        tokens: Iterable[str] = self.expand_group(self._expand_ops_text(group))
        if self.mode == 'rl':
            tokens = reversed(list(tokens))
        out = self.IDENTITY_UTT
        for token in tokens:
            out = self.compose_utt(self.token_to_utt(token), out)
        return out

    def to_utt(self, text: str) -> UTT:
        result = self.IDENTITY_UTT
        groups = self._groups_from_text(text)
        seq: Iterable[str] = groups if self.mode == 'lr' else reversed(groups)
        for group in seq:
            result = self.compose_utt(self.group_to_utt(group), result)
        return result

    def recognizes(self, token_or_group: str) -> bool:
        try:
            self.to_utt(token_or_group)
            return True
        except ValueError:
            return False

    def apply_utt(self, triad: Triad, utt: UTT) -> Triad:
        sigma, tp, tm = utt
        mode_in = self._mode_int(triad.mode())
        shift = tp if mode_in == 1 else tm
        root = (triad.root().pc + shift) % 12
        mode_out = sigma * mode_in
        return Triad(root, self._mode_str(mode_out), triad.root().accidental)

    def apply(self, triad: Triad, transformation: str) -> Triad:
        return self.apply_utt(triad, self.to_utt(transformation))

    @classmethod
    def _in_utt_literal(cls, expr: str, pos: int) -> bool:
        lt = expr.rfind('<', 0, pos)
        gt = expr.find('>', pos)
        return lt != -1 and gt != -1 and lt < pos < gt

    def find_object(self, expr: str) -> Tuple[str, str, str]:
        def in_delimited(pos: int) -> bool:
            depth_paren = expr.count('(', 0, pos) - expr.count(')', 0, pos)
            depth_brack = expr.count('[', 0, pos) - expr.count(']', 0, pos)
            depth_brace = expr.count('{', 0, pos) - expr.count('}', 0, pos)
            return depth_paren > 0 or depth_brack > 0 or depth_brace > 0

        for match in self.CANDIDATE_RE.finditer(expr):
            token = match.group(0)
            if self._in_utt_literal(expr, match.start()):
                continue
            if token and token[0] in '([{':
                try:
                    Triad.from_string(token)
                except ValueError:
                    continue
                return expr[:match.start()], token, expr[match.end():]

        for match in self.CANDIDATE_RE.finditer(expr):
            token = match.group(0)
            if self._in_utt_literal(expr, match.start()):
                continue
            if not (token and token[0].isalpha()):
                continue
            before = expr[match.start() - 1] if match.start() > 0 else ''
            tok_start = match.start()
            tok_end = match.end()

            j = tok_end
            while j < len(expr) and expr[j].isspace():
                j += 1
            if j < len(expr) and expr[j] in '+-Mm':
                tok_end = j + 1

            after = expr[tok_end] if tok_end < len(expr) else ''
            if before.isalpha() or after.isalpha() or after.isdigit() or in_delimited(match.start()):
                continue
            try:
                Triad.from_string(re.sub(r'\s+', '', expr[tok_start:tok_end]))
            except ValueError:
                continue
            return expr[:tok_start], expr[tok_start:tok_end], expr[tok_end:]

        raise ValueError("no object found in expression")

    def parse_object(self, token: str) -> Tuple[Triad, Dict[str, object]]:
        canon = re.sub(r'\s+', '', token.strip())
        triad = Triad.from_string(canon)
        sharp = triad.root().accidental != 'flat'

        if re.fullmatch(rf'\(\s*{self.NOTE_RE}\s*\)', canon):
            return triad, {'form': 'paren_bare', 'sharp': sharp}
        if re.fullmatch(rf'[\[\{{]\s*{self.NOTE_RE}\s*,\s*{self.NOTE_RE}\s*,\s*{self.NOTE_RE}\s*[\]\}}]', canon):
            return triad, {'form': 'triple', 'sharp': sharp}
        m = re.fullmatch(rf'\(\s*{self.NOTE_RE}\s*([Mm+\-])\s*\)', canon)
        if m:
            return triad, {'form': 'suffix', 'sharp': sharp, 'suf': m.group(1)}
        m = re.fullmatch(rf'\(\s*{self.NOTE_RE}\s*,\s*([+\-])\s*\)', canon)
        if m:
            return triad, {'form': 'paren', 'sharp': sharp}
        m = re.fullmatch(rf'{self.NOTE_RE}\s*([Mm+\-])', canon)
        if m:
            return triad, {'form': 'suffix', 'sharp': sharp, 'suf': m.group(1)}
        return triad, {'form': 'plain', 'sharp': sharp}

    def evaluate(self, expr: str) -> Triad:
        prefix, obj, suffix = self.find_object(expr)
        triad, _ = self.parse_object(obj)
        triad = self.apply(triad, prefix)
        triad = self.apply(triad, suffix)
        return triad

    @staticmethod
    def format_utt(u: UTT) -> str:
        return f"<{'+' if u[0] == 1 else '-'}, {u[1]}, {u[2]}>"

    def utt_order(self, u: UTT) -> Optional[int]:
        power = u
        for k in range(1, 25):
            if power == self.IDENTITY_UTT:
                return k
            power = self.compose_utt(u, power)
        return None

    @staticmethod
    def is_riemannian(u: UTT) -> bool:
        return (u[1] + u[2]) % 12 == 0

    def inspect(self, text: str) -> str:
        u = self.to_utt(text)
        kind = "mode-preserving" if u[0] == 1 else "mode-reversing"
        riemann = "Riemannian" if self.is_riemannian(u) else "non-Riemannian"
        order = self.utt_order(u)
        return (
            f"UTT: {self.format_utt(u)}\n"
            f"Type: {kind}, {riemann}; major +{u[1]}, minor +{u[2]}; order {order}"
        )

    @staticmethod
    def _to_unicode(name: str, pretty: bool) -> str:
        if not pretty:
            return name
        return name.replace('#', '♯').replace('b', '♭')

    def _format_root(self, pc: int, sharp: bool, upper: bool, root_hint: Optional[int], pretty: bool) -> str:
        pc %= 12
        if self.spelling == 'sharp':
            name = PC_TO_SHARP[pc]
        elif self.spelling == 'flat':
            name = PC_TO_FLAT[pc]
        elif self.spelling == 'auto':
            base = pc if root_hint is None else (root_hint % 12)
            name = PC_TO_FLAT[pc] if base in self.FLAT_ROOTS else PC_TO_SHARP[pc]
        else:
            name = PC_TO_SHARP[pc] if sharp else PC_TO_FLAT[pc]
        name = self._to_unicode(name, pretty)
        return name if upper else name.lower()

    def _full_name(self, pc: int, sharp: bool, root_hint: Optional[int]) -> str:
        pc %= 12
        if self.spelling == 'sharp':
            return NAME_SHARP[pc]
        if self.spelling == 'flat':
            return NAME_FLAT[pc]
        if self.spelling == 'auto':
            base = pc if root_hint is None else (root_hint % 12)
            return NAME_FLAT[pc] if base in self.FLAT_ROOTS else NAME_SHARP[pc]
        return NAME_SHARP[pc] if sharp else NAME_FLAT[pc]

    def _format_input_form(self, triad: Triad, input_style: Dict[str, object], pretty: bool) -> str:
        root = triad.root().pc
        mode = self._mode_int(triad.mode())
        sharp = bool(input_style.get('sharp', True))
        form = str(input_style.get('form', 'plain'))

        if form == 'paren_bare':
            return f"({self._format_root(root, sharp, mode == 1, root, pretty)})"
        if form == 'triple':
            parts = [
                self._format_root(n, sharp, mode == 1, root, pretty)
                for n in self._notes_of(root, mode)
            ]
            return '[' + ','.join(parts) + ']'
        if form == 'paren':
            return f"({self._format_root(root, sharp, True, root, pretty)},{'+' if mode == 1 else '-'})"
        suf = str(input_style.get('suf', ''))
        if suf in ('M', 'm'):
            return self._format_root(root, sharp, True, root, pretty) + ('M' if mode == 1 else 'm')
        if suf in ('+', '-'):
            return self._format_root(root, sharp, True, root, pretty) + ('+' if mode == 1 else '-')
        return self._format_root(root, sharp, mode == 1, root, pretty)

    def format_triad(
        self,
        triad: Triad,
        style: Optional[str] = None,
        input_style: Optional[Dict[str, object]] = None,
        pretty: bool = True,
    ) -> str:
        fmt = self.output_style if style is None else style
        if fmt not in ('input', 'short', 'tuple', 'spell'):
            raise ValueError("style must be input|short|tuple|spell")

        root = triad.root().pc
        mode = self._mode_int(triad.mode())
        sharp = triad.root().accidental != 'flat'

        if fmt == 'short':
            out = self._format_root(root, sharp, True, root, pretty) + ('+' if mode == 1 else '-')
        elif fmt == 'tuple':
            out = f"({self._format_root(root, sharp, True, root, pretty)},{'+' if mode == 1 else '-'})"
        elif fmt == 'spell':
            notes = [
                self._format_root(n, sharp, True, root, pretty)
                for n in self._notes_of(root, mode)
            ]
            out = '[' + ','.join(notes) + ']'
        else:
            if input_style is None:
                input_style = {'form': 'paren', 'sharp': sharp}
            out = self._format_input_form(triad, input_style, pretty)

        if self.show_description:
            quality = 'major' if mode == 1 else 'minor'
            out = f"{out} => {self._full_name(root, sharp, root)} {quality} triad"
        return out

    def evaluate_to_string(self, expr: str, style: Optional[str] = None, pretty: bool = True) -> str:
        prefix, obj, suffix = self.find_object(expr)
        triad, input_style = self.parse_object(obj)
        triad = self.apply(triad, prefix)
        triad = self.apply(triad, suffix)
        return self.format_triad(triad, style=style, input_style=input_style, pretty=pretty)

    def _tuple_label(self, triad: Triad, pretty: bool = True) -> str:
        return self.format_triad(triad, style='tuple', pretty=pretty)

    def iter_atomic_tokens(self, text: str) -> Iterator[str]:
        groups = self._groups_from_text(text)
        seq: Iterable[str] = groups if self.mode == 'lr' else reversed(groups)
        for group in seq:
            tokens = self.expand_group(group)
            toks: Iterable[str] = tokens if self.mode == 'lr' else reversed(tokens)
            for token in toks:
                expanded = self.COMPOUND_EXPANSION.get(token)
                if expanded is None:
                    yield token
                elif self.mode == 'lr':
                    for op in expanded:
                        yield op
                else:
                    for op in reversed(expanded):
                        yield op

    def format_steps(self, expr: str, pretty: bool = True) -> str:
        prefix, obj, suffix = self.find_object(expr)
        triad, _ = self.parse_object(obj)
        tokens = list(self.iter_atomic_tokens(prefix)) + list(self.iter_atomic_tokens(suffix))
        parts = [self._tuple_label(triad, pretty=pretty)]
        state = triad
        for token in tokens:
            state = self.apply(state, token)
            parts.append(f" {token} -> {self._tuple_label(state, pretty=pretty)}")
        n = len(tokens)
        return f"{n} step{'s' if n != 1 else ''}:\n  {''.join(parts)}"
