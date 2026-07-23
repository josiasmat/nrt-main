#!/usr/bin/env python3
"""Neo-Riemannian transformation evaluator.

Applies neo-Riemannian operators and Uniform Triadic Transformations (UTTs)
to major/minor triads (objects) and prints the result. Operators entered
without an object are normalized into a single UTT and inspected.
"""

import re
import sys

from triad import Triad, Note, find_triads, PC_TO_SHARP, PC_TO_FLAT, \
    NOTE_TO_PC, NAME_SHARP, NAME_FLAT
from transforms import NRT

from help import print_help


# --- Application order for juxtaposed operators ---
# 'lr' = left-to-right (L R  =>  apply L then R)   [default]
# 'rl' = right-to-left (L R  =>  apply R then L, i.e. L o R, math convention)
MODE = 'lr'

# --- Enharmonic spelling preference ---
# 'input' = inherit from the object (default) | 'sharp' | 'flat' | 'auto'
SPELLING = 'auto'

# --- Output style ---
# 'input' = inherit form from the object | 'short' | 'tuple' | 'spell'
OUTPUT_STYLE = 'input'
SHOW_DESCR = False   # append full description (e.g. "C major triad")
USE_COLOR = False   # set at startup; controls path: colouring

# Triads whose roots are conventionally written with flats (used by 'auto').
FLAT_ROOTS = {1, 3, 8, 10}   # Db, Eb, Ab, Bb

# Unicode accidentals for output.
SHARP_SIGN = '\u266F'   # ♯
FLAT_SIGN  = '\u266D'   # ♭

# ANSI colours for path: output.
C_MAJOR = '\033[92m'  # green
C_MINOR = '\033[36m'  # cian
C_OP    = '\033[97m'  # magenta
C_RESET = '\033[0m'


def _nrt():
    """Build an NRT engine from current global runtime settings."""
    return NRT(
        mode=MODE,
        output_style=OUTPUT_STYLE,
        spelling=SPELLING,
        show_description=SHOW_DESCR,
    )


def notes_of(root, mode):
    """Return the three pitch classes of a triad (mode 1 = major, -1 = minor)."""
    third = 4 if mode == 1 else 3
    return [root % 12, (root + third) % 12, (root + 7) % 12]


# --- Object detection / parsing ---
_NOTE_RE = r'[A-Ga-g](?:[#b♯♭])?'
_CANDIDATE_RE = re.compile(
    rf'''
    \(\s*{_NOTE_RE}\s*,\s*[+\-Mm]\s*\) |
    [\[\{{]\s*{_NOTE_RE}\s*,\s*{_NOTE_RE}\s*,\s*{_NOTE_RE}\s*[\]\}}] |
    \(\s*{_NOTE_RE}(?:[+\-Mm]|min|minor)?\s*\) |
    {_NOTE_RE}(?:[+\-Mm]|min|minor)?
    ''',
    re.VERBOSE,
)


def _root_is_sharp(root):
    """Heuristic: True if the root should be treated as sharp/natural."""
    if not isinstance(root, Note):
        raise TypeError(f"root must be a Note, got {type(root).__name__}")
    return root.accidental != 'flat'


def _style_for_token(token, triad):
    """Infer the input style dictionary for output formatting."""
    sharp = _root_is_sharp(triad.root())

    if re.fullmatch(rf'\(\s*{_NOTE_RE}\s*\)', token):
        return {'form': 'paren_bare', 'sharp': sharp}
    if re.fullmatch(rf'[\[\{{]\s*{_NOTE_RE}\s*,\s*{_NOTE_RE}\s*,\s*{_NOTE_RE}\s*[\]\}}]', token):
        return {'form': 'triple', 'sharp': sharp}

    m = re.fullmatch(rf'\(\s*{_NOTE_RE}\s*([Mm+\-])\s*\)', token)
    if m:
        return {'form': 'suffix', 'sharp': sharp, 'suf': m.group(1)}

    m = re.fullmatch(rf'\(\s*{_NOTE_RE}\s*,\s*([+\-])\s*\)', token)
    if m:
        return {'form': 'paren', 'sharp': sharp}

    m = re.fullmatch(rf'{_NOTE_RE}\s*([Mm+\-])', token)
    if m:
        return {'form': 'suffix', 'sharp': sharp, 'suf': m.group(1)}

    return {'form': 'plain', 'sharp': sharp}


def parse_object(s):
    """Parse an object token; return (root, mode, style)."""
    triad, style = _nrt().parse_object(s.strip())
    mode = 1 if triad.mode() == '+' else -1
    return triad.root().pc, mode, style


def _in_utt_literal(expr, pos):
    """True if position `pos` falls inside a '<...>' UTT literal."""
    return _nrt()._in_utt_literal(expr, pos)


def find_object(expr):
    """Split an expression into (prefix, object, suffix).

    First look for a delimited object ((C), [C,E,G], {C,E,G}); if none is a
    real object, fall back to a bare object token (Cm, C+, c, ...). Anything
    inside a '<...>' UTT literal is skipped.
    """
    return _nrt().find_object(expr)


def has_object(expr):
    """True if the expression contains a triad object."""
    return bool(find_triads(expr))


# --- UTT algebra --------------------------------------------------------
# A UTT is the triple <sigma, t+, t->:
#   sigma in {+1, -1} : keep (+1) or invert (-1) the mode
#   t+ : transposition applied to a MAJOR triad
#   t- : transposition applied to a MINOR triad
IDENTITY_UTT = NRT.IDENTITY_UTT


def utt(root, mode, sigma, tp, tm):
    """Apply a UTT <sigma, t+, t-> to a triad (root, mode)."""
    shift = tp if mode == 1 else tm
    return (root + shift) % 12, sigma * mode


def compose_utt(u2, u1):
    """Return the single UTT equal to applying u1 first, then u2 (u2 o u1).

    Hook's composition law:
        <s2,u+,u-> o <s1,t+,t-> = <s1*s2, t+ + u^(s1), t- + u^(-s1)>
    """
    return NRT.compose_utt(u2, u1)


# Neo-Riemannian generators as UTT triples <sigma, t+, t->.
UTT_TABLE = dict(NRT().utt_table)


# --- Path generator presets --------------------------------------------
# Each preset is a tuple of operator *tokens* understood by token_to_utt.
# 'plr'  : classic neo-Riemannian P/L/R group (default).
# 'hyer' : Hyer's generators — adds the Dominant D1 (down a perfect fifth).
# 'lr'   : L/R only (LR-cycles; graph is NOT fully connected).
PATH_PRESETS = {
    'plr':  ('P', 'L', 'R'),
    'hyer': ('D6', 'L', 'R', 'P'),
    'lr':   ('L', 'R'),
}
DEFAULT_PATH_OPS = 'plr'


# Reverse lookup: UTT triple -> list of canonical names that produce it.
# Order matters for display (most idiomatic first).
_CANON_NAMES = [
    ('P',  "P (parallel)"),
    ('L',  "L (leittonwechsel)"),
    ('R',  "R (relative)"),
    ('N',  "N (nebenverwandt)"),
    ('H',  "H (hexatonic pole)"),
    ('S',  "S (slide)"),
    ("P'", "P' (P-prime)"),
    ("L'", "L' (L-prime)"),
    ("R'", "R' (R-prime)"),
]


def _canonical_names(u):
    """Named generators (and useful aliases) equal to this UTT."""
    names = [label for key, label in _CANON_NAMES if UTT_TABLE[key] == u]
    # Octatonic pole: <-,6,6> is not a named generator but is idiomatic.
    if u == (-1, 6, 6):
        names.append("octatonic pole")
    return names


def _transposition_form(u):
    """Return Tn / TnI form when the UTT is a pure transposition or inversion."""
    sigma, tp, tm = u
    if tp != tm:
        return None
    if sigma == 1:
        return "T0 (identity)" if tp == 0 else f"T{tp}"
    return f"T{tp}I"   # inversion; T0I == P


def _schritt_wechsel(u):
    """Return the Sn/Wn form if the UTT is a pure Schritt or Wechsel."""
    sigma, tp, tm = u
    if sigma == 1 and (tp + tm) % 12 == 0:
        return f"S{tp} (Schritt)"
    if sigma == -1 and (tm + (-tp)) % 12 == 0:  # <-,-n,n>  =>  n = tm
        return f"W{tm} (Wechsel)"
    return None


def _obverse(a, b, c):
    """Compose three named generators left-to-right (Morris obverse forms)."""
    u = IDENTITY_UTT
    for name in (a, b, c):
        u = compose_utt(UTT_TABLE[name], u)
    return u


from collections import deque

_PLR_CACHE = None


_PATH_CACHE = {}   # key: tuple(gens) -> {utt: shortest word}


def _gen_utts(gens):
    """Map generator tokens to (name, utt) pairs, validating each token."""
    out = []
    for g in gens:
        out.append((g, token_to_utt(g)))
    return out


def _build_paths(gens):
    """BFS over the given generators: each reachable UTT -> shortest word.

    The 'word' is the concatenation of generator tokens (space-separated
    when a token is longer than one character, e.g. 'D1').
    """
    pairs = _gen_utts(gens)
    start = IDENTITY_UTT
    paths = {start: []}          # store as list of tokens
    q = deque([start])
    while q:
        cur = q.popleft()
        for name, gu in pairs:
            nxt = compose_utt(gu, cur)
            if nxt not in paths:
                paths[nxt] = paths[cur] + [name]
                q.append(nxt)
    return paths


def _shortest_word(u, gens):
    """Shortest generator word equal to u, or None if u is unreachable."""
    key = tuple(gens)
    if key not in _PATH_CACHE:
        _PATH_CACHE[key] = _build_paths(gens)
    word = _PATH_CACHE[key].get(u)
    return word if word else None


def _shortest_plr(u):
    """Backwards-compatible shortest P/L/R word (used by describe_utt)."""
    word = _shortest_word(u, PATH_PRESETS['plr'])
    return ''.join(word) if word else None


def _all_shortest(start, goal, gens):
    """All shortest paths between two triads using the given generators.

    Returns a list of paths; each path is a list of (op_token, state) steps.
    Empty outer list = unreachable; a single empty path = start == goal.
    """
    if start == goal:
        return [[]]

    pairs = _gen_utts(gens)
    dist = {start: 0}
    preds = {start: []}
    frontier = [start]
    goal_depth = None

    depth = 0
    while frontier and goal_depth is None:
        depth += 1
        nxt_frontier = []
        for cur in frontier:
            for name, gu in pairs:
                nxt = utt(cur[0], cur[1], *gu)
                if nxt in dist and dist[nxt] < depth:
                    continue
                if nxt not in dist:
                    dist[nxt] = depth
                    preds[nxt] = []
                    nxt_frontier.append(nxt)
                if dist[nxt] == depth:
                    preds[nxt].append((name, cur))
        if goal in dist and dist[goal] == depth:
            goal_depth = depth
        frontier = nxt_frontier

    if goal not in dist:
        return []

    def build(state):
        if not preds[state]:
            return [[]]
        paths = []
        for op, prev in preds[state]:
            for sub in build(prev):
                paths.append(sub + [(op, state)])
        return paths

    return build(goal)


# Morris (1998) obverse transformations.
UTT_TABLE["P'"] = _obverse('R', 'P', 'L')   # P' = RPL
UTT_TABLE["L'"] = _obverse('R', 'L', 'P')   # L' = RLP
UTT_TABLE["R'"] = _obverse('L', 'R', 'P')   # R' = LRP


def _parse_sigma(tok):
    """Parse a sigma field: '+', '-', '+1', '-1', '1'."""
    return NRT._parse_sigma(tok)


def parse_utt_literal(s):
    """Parse a literal UTT '<sigma,tp,tm>' into a triple."""
    return _nrt().parse_utt_literal(s)


def token_to_utt(token):
    """Convert one operator token to a UTT triple.

    Recognized: P L R N H S (and P' L' R'); Tn, Dn, Sn (Schritt), Wn
    (Wechsel), In (Inversion), and literal <...> UTTs.
    """
    return _nrt().token_to_utt(token)


# --- Operator tokenization / reduction ---
def expand_group(group):
    """Split a compact operator string into tokens.

    Handles P L R N H, the primes P' L' R', bare Slide S, the parametrized
    families T/D/S/W/I (each optionally signed), and literal <...> UTTs.
    """
    return _nrt().expand_group(group)


def group_to_utt(group):
    """Reduce a compact operator group to a single normalized UTT.

    In 'lr' mode tokens apply left to right: 't1 t2 t3' == t3 o t2 o t1.
    In 'rl' mode tokens apply right to left: 't1 t2 t3' == t1 o t2 o t3.
    """
    return _nrt().group_to_utt(group)


def side_to_utt(text):
    """Reduce one side (prefix or suffix) of an expression to a single UTT."""
    return _nrt().to_utt(text)


def apply_side(state, text):
    """Apply the operators of one side to (root, mode)."""
    root, mode = state
    return utt(root, mode, *side_to_utt(text))


# Canonical decomposition of compound operators into P/L/R generators.
# Matches UTT_TABLE / _obverse definitions (H=PLP, N=PLR, S=LPR, primes=obverse).
COMPOUND_EXPANSION = dict(NRT.COMPOUND_EXPANSION)


def _iter_side_tokens(text):
    """Yield atomic operator tokens of one side in application order.

    Preserves the user's sequence exactly (no shortest-path collapsing).
    Compound operators (H, N, S, P', L', R') are expanded into their
    canonical P/L/R generators. Application order respects MODE.
    """
    yield from _nrt().iter_atomic_tokens(text)


# --- UTT inspection ---
def format_utt(u):
    """Render a UTT triple as '⟨sigma, t+, t-⟩'."""
    sigma, tp, tm = u
    return f"⟨{'+' if sigma == 1 else '-'}, {tp}, {tm}⟩"


def utt_order(u):
    """Order of a UTT in the group (smallest k with U^k = identity)."""
    power = u
    for k in range(1, 25):
        if power == IDENTITY_UTT:
            return k
        power = compose_utt(u, power)
    return None


def is_riemannian(u):
    """True if the UTT is Riemannian (dualistic).

    Mode-reversing: t+ + t- == 0 (mod 12).
    Mode-preserving: t+ == t-  (pure transposition, commutes trivially).
    """
    return (u[1] + u[2]) % 12 == 0


def describe_utt(u):
    """Human-readable description of a UTT, with equivalent forms."""
    sigma, tp, tm = u
    kind = "mode-preserving" if sigma == 1 else "mode-reversing"
    rmn = "Riemannian" if is_riemannian(u) else "non-Riemannian"

    lines = [f"  UTT  : {format_utt(u)}"]
    lines.append(f"  Type : {kind}, {rmn}; "
                 f"major +{tp}, minor +{tm}; order {utt_order(u)}")

    equivalents = []

    names = _canonical_names(u)
    if names:
        equivalents.extend(names)

    tn = _transposition_form(u)
    if tn:
        equivalents.append(tn)

    sw = _schritt_wechsel(u)
    if sw:
        equivalents.append(sw)

    plr = _shortest_plr(u)
    if plr is not None and len(plr) > 1:
        equivalents.append(f"{plr} (shortest P/L/R)")

    # De-duplicate while preserving order.
    seen = set()
    uniq = [e for e in equivalents if not (e in seen or seen.add(e))]

    if uniq:
        lines.append("  Also : " + "; ".join(uniq))
    return "\n".join(lines)


def inspect(expr):
    """Normalize an object-less transformation and show its equivalent forms."""
    u = side_to_utt(expr)
    return describe_utt(u)


# --- Output formatting ---
def format_root(pc, sharp, upper=True, root_hint=None):
    """Format a single pitch class, honouring the spelling preference."""
    pc %= 12
    if SPELLING == 'sharp':
        name = PC_TO_SHARP[pc]
    elif SPELLING == 'flat':
        name = PC_TO_FLAT[pc]
    elif SPELLING == 'auto':
        base = root_hint if root_hint is not None else pc
        name = PC_TO_FLAT[pc] if (base % 12) in FLAT_ROOTS else PC_TO_SHARP[pc]
    else:  # 'input'
        name = (PC_TO_SHARP if sharp else PC_TO_FLAT)[pc]
    name = _to_unicode(name)
    return name if upper else name.lower()


def _to_unicode(name):
    """Replace ASCII accidentals with Unicode sharp/flat signs."""
    return name.replace('#', SHARP_SIGN).replace('b', FLAT_SIGN)


def _full_name(pc, sharp, root_hint=None):
    """Full spelled-out name of a pitch class (e.g. 'E-flat')."""
    pc %= 12
    if SPELLING == 'sharp':
        return NAME_SHARP[pc]
    if SPELLING == 'flat':
        return NAME_FLAT[pc]
    if SPELLING == 'auto':
        base = root_hint if root_hint is not None else pc
        return NAME_FLAT[pc] if (base % 12) in FLAT_ROOTS else NAME_SHARP[pc]
    return NAME_SHARP[pc] if sharp else NAME_FLAT[pc]


def describe(root, mode, sharp):
    """Return a description like 'E-flat minor triad'."""
    quality = 'major' if mode == 1 else 'minor'
    return f"{_full_name(root, sharp, root_hint=root)} {quality} triad"


def sigma(mode, chars = ['+','-']):
    """Return the sigma sign for a triad mode."""
    return chars[0] if mode == 1 else chars[1]


def spell_triad(root, sharp, mode):
    """Return a list of the three spelled-out notes of a triad."""
    parts = [_full_name(n, sharp, root_hint=root) for n in notes_of(root, mode)]
    return '[' + ','.join(parts) + ']'


def format_output(root, mode, style):
    """Render the resulting triad according to OUTPUT_STYLE and SHOW_DESCR."""
    sharp = style.get('sharp', True)

    if OUTPUT_STYLE == 'short':
        chord = format_root(root, sharp, True, root_hint=root) + sigma(mode, '+-')
    elif OUTPUT_STYLE == 'tuple':
        chord = (f'({format_root(root, sharp, True, root_hint=root)},'
                 f'{sigma(mode)})')
    elif OUTPUT_STYLE == 'spell':
        chord = spell_triad(root, sharp, mode)
    else:  # 'input' — inherit the object's form
        chord = _format_input_form(root, mode, style)

    return f"{chord} ⇒ {describe(root, mode, sharp)}" if SHOW_DESCR else chord


def _triad_label(root, mode):
    """Render a triad as a tuple label like (C,+), padded and coloured."""
    sharp = mode == 1
    text = f'({format_root(root, sharp, True, root_hint=root)},{sigma(mode)})'
    if not USE_COLOR:
        return text
    colour = C_MAJOR if mode == 1 else C_MINOR
    return f"{colour}{text}{C_RESET}"


def _op_label(op):
    """Render an operator, coloured orange if enabled."""
    return f"{C_OP}{op}{C_RESET}" if USE_COLOR else op


SUP = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
       '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'}


def _superscript(n):
    """Render an integer as Unicode superscript digits."""
    return ''.join(SUP[d] for d in str(n))


def compress_word(word):
    """Compress a P/L/R word using power notation for repeated segments.

    Examples: 'LRLR' -> '(LR)²', 'PP' -> 'P²', 'LRLRP' -> '(LR)²P'.
    """
    n = len(word)
    out = []
    i = 0
    while i < n:
        best_block, best_reps, best_span = word[i], 1, 1
        # Try every block length; keep the one covering the most characters,
        # breaking ties toward the shorter (more compressed) block.
        for blen in range(1, n - i + 1):
            block = word[i:i + blen]
            reps = 1
            while (word[i + reps * blen: i + (reps + 1) * blen] == block
                   and i + (reps + 1) * blen <= n):
                reps += 1
            span = reps * blen
            if reps >= 2 and (span > best_span
                              or (span == best_span and blen < len(best_block))):
                best_block, best_reps, best_span = block, reps, span
        if best_reps >= 2:
            token = (f"({best_block})" if len(best_block) > 1 else best_block)
            out.append(f"{token}{_superscript(best_reps)}")
            i += best_span
        else:
            out.append(word[i])
            i += 1
    return ''.join(out)


def resolve_path_ops(spec):
    """Turn an --ops value into a validated tuple of generator tokens.

    Accepts a preset name (plr, hyer, lr) or an arbitrary sequence of
    operator tokens separated by spaces or commas, e.g. 'P L D1' or 'PLR'.
    A bare letter sequence like 'PLR' is split into single-letter tokens.
    Raises ValueError on unknown/invalid tokens.
    """
    spec = spec.strip()
    key = spec.lower()
    if key in PATH_PRESETS:
        return PATH_PRESETS[key]

    # Explicit separators -> take tokens verbatim (allows multi-char like D1).
    if re.search(r'[\s,]', spec):
        tokens = [t for t in re.split(r'[\s,]+', spec) if t]
    else:
        # Bare string: reuse the operator tokenizer (handles P L R, D1, ...).
        tokens = expand_group(spec)

    if not tokens:
        raise ValueError("no operations specified for --ops")

    # Validate: every token must reduce to a UTT.
    for t in tokens:
        try:
            token_to_utt(t)
        except ValueError:
            raise ValueError(f"invalid operation token: {t!r}")
    return tuple(tokens)


def _pretty_token(token):
    """Render an operator token for display: letter + superscript digits.

    Single-letter tokens (P, L, R) are returned unchanged; parametrized
    tokens like 'D6' become 'D⁶' with no surrounding spaces.
    """
    m = re.fullmatch(r'([A-Z])(-?\d+)', token)
    if not m:
        return token
    letter, num = m.group(1), m.group(2)
    sign = ''
    if num.startswith('-'):
        sign, num = '\u207B', num[1:]   # superscript minus
    return letter + sign + _superscript(num)


def format_path(start, goal, gens=None):
    """Build all shortest transformational processes between two triads."""
    if gens is None:
        gens = PATH_PRESETS[DEFAULT_PATH_OPS]

    paths = _all_shortest(start, goal, gens)
    label = '/'.join(_pretty_token(t) for t in gens)

    if not paths:
        return (f"no path from {_triad_label(*start)} to "
                f"{_triad_label(*goal)} using {{{label}}} (unreachable)")
    if paths == [[]]:
        return f"{_triad_label(*start)} = {_triad_label(*goal)} (identity)"

    def render(steps):
        tokens = [op for op, _ in steps]
        word = ''.join(tokens)                    # sort key
        # Compress only makes sense for single-char P/L/R words.
        if all(len(t) == 1 for t in tokens):
            disp = compress_word(word)
        else:
            disp = ''.join(_pretty_token(t) for t in tokens)
        coloured_word = _op_label(disp)
        parts = [_triad_label(*start)]
        for op, state in steps:
            parts.append(f" {_op_label(_pretty_token(op))} → {_triad_label(*state)}")
        return word, f"{coloured_word}: " + ''.join(parts)

    rendered = sorted((render(p) for p in paths),
                      key=lambda x: (len(x[0]), x[0]))
    n = len(rendered)
    header = (f"{n} shortest path{'s' if n != 1 else ''} "
              f"(length {len(paths[0])}, ops {{{label}}}):")
    return header + "\n" + "\n".join("  " + line for _, line in rendered)


def _format_input_form(root, mode, style):
    """Render the triad in the same form as the input object."""
    sharp = style.get('sharp', True)
    form = style['form']
    if form == 'paren_bare':
        return f'({format_root(root, sharp, upper=(mode == 1), root_hint=root)})'
    if form == 'triple':
        parts = [format_root(n, sharp, mode == 1, root_hint=root)
                 for n in notes_of(root, mode)]
        return '[' + ','.join(parts) + ']'
    if form == 'paren':
        return (f'({format_root(root, sharp, True, root_hint=root)},'
                f'{"+" if mode == 1 else "-"})')
    # 'suffix' or 'plain'
    suf = style.get('suf', '')
    if suf in ('M', 'm'):
        return format_root(root, sharp, True, root_hint=root) + \
            ('M' if mode == 1 else 'm')
    if suf in ('+', '-'):
        return format_root(root, sharp, True, root_hint=root) + \
            ('+' if mode == 1 else '-')
    return format_root(root, sharp, upper=(mode == 1), root_hint=root)


# --- Evaluation ---
def evaluate(expr):
    """Evaluate an expression: apply its operators to the object."""
    prefix, obj, suffix = find_object(expr)
    root, mode, style = parse_object(obj)
    root, mode = apply_side((root, mode), prefix)
    root, mode = apply_side((root, mode), suffix)
    return format_output(root, mode, style), mode


def format_steps(expr):
    """Decompose an expression into per-operator steps (like path: output).

    Keeps the operators as given by the user (compounds expanded to atomic
    generators); does NOT reduce to a shortest path.
    """
    prefix, obj, suffix = find_object(expr)
    root, mode, style = parse_object(obj)

    tokens = list(_iter_side_tokens(prefix)) + list(_iter_side_tokens(suffix))
    parts = [_triad_label(root, mode)]
    for tok in tokens:
        root, mode = utt(root, mode, *token_to_utt(tok))
        parts.append(f" {_op_label(_pretty_token(tok))} → {_triad_label(root, mode)}")

    n = len(tokens)
    header = f"{n} step{'s' if n != 1 else ''}:"
    return f"{header}\n  {''.join(parts)}"


def parse_path(text):
    """Parse 'O1 O2' into two (root, mode) states via find_object."""
    prefix, obj1, rest = find_object(text)
    if prefix.strip():
        raise ValueError(f"unexpected text before first triad: {prefix!r}")
    root1, mode1, _ = parse_object(obj1)

    mid, obj2, tail = find_object(rest)
    if tail.strip():
        raise ValueError(f"unexpected text after second triad: {tail!r}")
    root2, mode2, _ = parse_object(obj2)
    return (root1, mode1), (root2, mode2)


# --- Terminal colour ---
def colorize(text, mode):
    """Colour major results green and minor results cyan (TTY only)."""
    code = C_MAJOR if mode == 1 else C_MINOR
    return f'{code}{text}{C_RESET}'


def _parse_flags(args):
    """Extract --sharp/--flat/--auto/--input from args; return (spelling, rest)."""
    spelling, rest = None, []
    aliases = {
        '--sharp': 'sharp', '-s': 'sharp',
        '--flat': 'flat',   '-f': 'flat',
        '--auto': 'auto',   '-a': 'auto',
        '--input': 'input', '-i': 'input',
    }
    for a in args:
        if a in aliases:
            spelling = aliases[a]
        else:
            rest.append(a)
    return spelling, rest


def _is_cmd(cmd, line):
    return line.startswith(cmd + ' ') \
        or line.startswith(cmd + ':') \
        or line == cmd


def repl(use_color):
    """Interactive read-eval-print loop."""
    print("Neo-Riemannian transformations evaluator.")
    print("Type 'help' for instructions.  'quit' or 'exit' to exit.\n")
    global SPELLING, OUTPUT_STYLE, SHOW_DESCR, MODE, USE_COLOR
    USE_COLOR = use_color
    while True:
        try:
            line = input(">>> ").strip()
        except EOFError:
            print()
            break

        if not line:
            continue

        low = line.lower()

        if low in ('quit', 'exit'):
            break

        if low == 'help':
            print_help()
            continue

        # inspect <operators> — normalize a transformation to a single UTT
        if _is_cmd('inspect', low):
            arg = re.split(r'[:\s]+', line, maxsplit=1)
            if len(arg) == 1:
                print("Error: inspect requires operators "
                      "(e.g. inspect PLR)\n")
                continue
            try:
                print(inspect(arg[1]) + "\n")
            except Exception as e:
                print(f"Error: {e}\n")
            continue

        # path:<O1> <O2> [--ops SET] — shortest path between two triads
        if _is_cmd('path', low):
            arg = re.split(r'[:\s]+', line, maxsplit=1)
            if len(arg) == 1 or not arg[1].strip():
                print("Error: path requires two triads "
                      "(e.g. path: (C,+) (G,-)  or  path --ops hyer C G)\n")
                continue
            body = arg[1]
            # Extract an optional --ops SET (SET may be a preset or tokens).
            ops_spec = DEFAULT_PATH_OPS
            m = re.search(r'--ops[=\s]+(\S+)', body)
            if m:
                ops_spec = m.group(1)
                body = (body[:m.start()] + body[m.end():]).strip()
            try:
                gens = resolve_path_ops(ops_spec)
                start, goal = parse_path(body)
                print(format_path(start, goal, gens) + "\n")
            except Exception as e:
                print(f"Error: {e}\n")
            continue

        # follow:<expr> / follow <expr> — evaluate and show step-by-step process
        if _is_cmd('follow', low):
            arg = re.split(r'[:\s]+', line, maxsplit=1)
            if len(arg) == 1 or not arg[1].strip():
                print("Error: follow requires an expression "
                      "(e.g. follow: (C,+)N)\n")
                continue
            expr = arg[1].strip()
            try:
                print(format_steps(expr) + "\n")
            except Exception as e:
                print(f"Error: {e}\n")
            continue

        # spell [sharp|flat|auto|input]
        if _is_cmd('spell', low):
            arg = re.split(r'[:\s]+', low)
            if len(arg) == 1:
                print(f"spelling = {SPELLING}\n")
            elif arg[1] in ('sharp', 'flat', 'auto', 'input'):
                SPELLING = arg[1]
                print(f"spelling = {SPELLING}\n")
            else:
                print(f"Error: unknown spelling {arg[1]!r} "
                      f"(use sharp|flat|auto|input)\n")
            continue

        # out [input|short|tuple|spell]
        if _is_cmd('out', low):
            arg = re.split(r'[:\s]+', low)
            if len(arg) == 1:
                print(f"output style = {OUTPUT_STYLE}\n")
            elif arg[1] in ('input', 'short', 'tuple', 'spell'):
                OUTPUT_STYLE = arg[1]
                print(f"output style = {OUTPUT_STYLE}\n")
            else:
                print(f"Error: unknown output style {arg[1]!r} "
                      f"(use input|short|tuple|spell)\n")
            continue

        # desc [on|off]
        if _is_cmd('desc', low):
            arg = re.split(r'[:\s]+', low)
            if len(arg) == 1:
                print(f"description = {'on' if SHOW_DESCR else 'off'}\n")
            elif arg[1] in ('on', 'off'):
                SHOW_DESCR = (arg[1] == 'on')
                print(f"description = {'on' if SHOW_DESCR else 'off'}\n")
            else:
                print(f"Error: unknown description setting {arg[1]!r} "
                      f"(use on|off)\n")
            continue

        try:
            m = re.search(r'\s*--follow\b', line)
            expr = (line[:m.start()] + line[m.end():]).strip() if m else line
            if m:
                print(format_steps(expr) + "\n")
            else:
                text, mode = evaluate(expr)
                out = colorize(text, mode) if (use_color and mode is not None) else text
                print(out + "\n")
        except Exception as e:
            print(f"Error: {e}\n")


def main():
    global SPELLING, USE_COLOR
    if '--test' in sys.argv[1:]:
        from tests import run_tests
        ok = run_tests()
        sys.exit(0 if ok else 1)
    use_color = sys.stdout.isatty()
    USE_COLOR = use_color
    spelling, rest = _parse_flags(sys.argv[1:])
    if spelling:
        SPELLING = spelling
    if rest:
        if rest[0] == 'inspect':
            print(inspect(' '.join(rest[1:])) + "\n")
        elif rest[0] == 'path':
            path_args = rest[1:]
            ops_spec = DEFAULT_PATH_OPS
            filtered = []
            i = 0
            while i < len(path_args):
                a = path_args[i]
                if a == '--ops' and i + 1 < len(path_args):
                    ops_spec = path_args[i + 1]
                    i += 2
                    continue
                if a.startswith('--ops='):
                    ops_spec = a.split('=', 1)[1]
                    i += 1
                    continue
                filtered.append(a)
                i += 1
            gens = resolve_path_ops(ops_spec)
            start, goal = parse_path(' '.join(filtered))
            print(format_path(start, goal, gens) + "\n")
        elif rest[0] == 'follow':
            expr = ' '.join(rest[1:]).strip()
            if not expr:
                print("Error: follow requires an expression")
                sys.exit(1)
            print(format_steps(expr) + "\n")
        else:
            joined = ' '.join(rest)
            if joined.startswith('follow:'):
                expr = joined.split(':', 1)[1].strip()
                if not expr:
                    print("Error: follow requires an expression")
                    sys.exit(1)
                print(format_steps(expr) + "\n")
                return
            if joined.lower().startswith('follow '):
                expr = joined[7:].strip()
                if not expr:
                    print("Error: follow requires an expression")
                    sys.exit(1)
                print(format_steps(expr) + "\n")
                return
            m = re.search(r'\s*--follow\b', joined)
            if m:
                expr = (joined[:m.start()] + joined[m.end():]).strip()
                print(format_steps(expr) + "\n")
            else:
                text, mode = evaluate(joined)
                out = colorize(text, mode) if (use_color and mode is not None) else text
                print(out + "\n")
    else:
        repl(use_color)


if __name__ == '__main__':
    main()
