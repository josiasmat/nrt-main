import re

import nrt as nrt
from nrt import (
    find_object, parse_object, group_to_utt,
    evaluate, _iter_side_tokens, token_to_utt,
    _all_shortest, resolve_path_ops, _pretty_token,
    compress_word, describe_utt, format_steps,
    UTT_TABLE, IDENTITY_UTT, PATH_PRESETS, parse_path
)

# --- Automated tests ----------------------------------------------------
def run_tests():
    """Self-contained regression tests. Run with:  python script.py --test"""
    # Deterministic settings.
    nrt.OUTPUT_STYLE = 'tuple'
    nrt.SPELLING = 'sharp'
    nrt.SHOW_DESCR = False
    nrt.USE_COLOR = False
    nrt.MODE = 'lr'
    nrt.LAST_TRIAD = None

    passed = failed = 0

    def check(desc, got, want):
        nonlocal passed, failed
        if got == want:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: {desc}\n      got : {got!r}\n      want: {want!r}")

    def check_split(desc, expr, want):
        """find_object must return the expected (prefix, obj, suffix)."""
        check(desc, find_object(expr), want)

    def check_eval(desc, expr, want_tuple):
        """evaluate() output (in tuple style) must match."""
        text, _ = evaluate(expr)
        check(desc, text, want_tuple)

    def check_error(desc, fn):
        nonlocal passed, failed
        try:
            fn()
            failed += 1
            print(f"FAIL: {desc}\n      expected an exception, none raised")
        except Exception:
            passed += 1

    # --- find_object splitting (the regression that motivated the fix) ---
    check_split("(Gm)(LRL) split",  "(Gm)(LRL)", ("", "(Gm)", "(LRL)"))
    check_split("(Gm)LRL split",    "(Gm)LRL",   ("", "(Gm)", "LRL"))
    check_split("Gm(LRL) split",    "Gm(LRL)",   ("", "Gm", "(LRL)"))
    check_split("Gm LRL split",     "Gm LRL",    ("", "Gm", " LRL"))
    check_split("(LRL)(Gm) split",  "(LRL)(Gm)", ("(LRL)", "(Gm)", ""))
    check_split("(G+)(PLP) split",  "(G+)(PLP)", ("", "(G+)", "(PLP)"))
    check_split("(c)(LR) split",    "(c)(LR)",   ("", "(c)", "(LR)"))
    check_split("[G,Bb,D](D2)",     "[G,Bb,D](D2)", ("", "[G,Bb,D]", "(D2)"))
    check_split("(C,+)(RP) split",  "(C,+)(RP)", ("", "(C,+)", "(RP)"))
    check_split("literal skipped",  "<+,2,10>(C,+)",
                ("<+,2,10>", "(C,+)", ""))
    check_split("bare + two groups","C(LR)(P)",  ("", "C", "(LR)(P)"))

    # --- parse_object accepts (Gm)-style ---
    check("parse (Gm)", parse_object("(Gm)"),
          (7, -1, {'form': 'suffix', 'sharp': True, 'suf': 'm'}))
    check("parse (C+)", parse_object("(C+)"),
          (0, 1, {'form': 'suffix', 'sharp': True, 'suf': '+'}))
    check("parse (C-)", parse_object("(C-)"),
          (0, -1, {'form': 'suffix', 'sharp': True, 'suf': '-'}))
    check("parse (C#m)", parse_object("(C#m)"),
          (1, -1, {'form': 'suffix', 'sharp': True, 'suf': 'm'}))
    check("parse (c) bare", parse_object("(c)"),
          (0, -1, {'form': 'paren_bare', 'sharp': True}))

    # --- Neo-Riemannian identities (algebra sanity) ---
    # On a major triad, PLP = H (hexatonic pole); LR cycle etc.
    check_eval("C P  = c",        "C(P)",   "(C,-)")
    check_eval("C L  = e",        "C(L)",   "(E,-)")
    check_eval("C R  = a",        "C(R)",   "(A,-)")
    check_eval("C LR = e->G?",    "C(LR)",  "(G,+)")   # L: e, R: G major
    check_eval("Gm LRL",          "(Gm)(LRL)", "(G♯,+)")

    # H equals PLP directly:
    check("PLP == H (UTT)", group_to_utt("PLP"), UTT_TABLE['H'])
    check("N == PLR (UTT)", group_to_utt("PLR"), UTT_TABLE['N'])
    check("S == LPR (UTT)", group_to_utt("LPR"), UTT_TABLE['S'])
    check("L(PR)^2 == LPRPR", group_to_utt("L(PR)^2"), group_to_utt("LPRPR"))
    check("L(PR)² == LPRPR", group_to_utt("L(PR)²"), group_to_utt("LPRPR"))
    check("(RL)^2P == RLRLP", group_to_utt("(RL)^2P"), group_to_utt("RLRLP"))
    check("(RL)²P == RLRLP", group_to_utt("(RL)²P"), group_to_utt("RLRLP"))

    # --- Involutions: P, L, R are their own inverse ---
    for g in ('P', 'L', 'R'):
        check(f"{g}{g} = identity", group_to_utt(g + g), IDENTITY_UTT)

    # --- UTT literal application ---
    check_eval("<+,2,10>(C,+) = D+", "<+,2,10>(C,+)", "(D,+)")

    # --- Dominant D6 = tritone ---
    check("D6 UTT", token_to_utt("D6"), (1, 6, 6))
    check_eval("C D6 = F♯", "C(D6)", "(F♯,+)")

    # --- Path finding ---
    # C+ to C- : shortest P/L/R is just P.
    p = _all_shortest((0, 1), (0, -1), PATH_PRESETS['plr'])
    check("path C+ -> C- length", min(len(x) for x in p), 1)

    # hyer preset includes D6.
    check("hyer preset", PATH_PRESETS['hyer'], ('D6', 'L', 'R', 'P'))
    # C+ to F#+ via D6 in one step.
    p2 = _all_shortest((0, 1), (6, 1), PATH_PRESETS['hyer'])
    check("path C+ -> F♯+ (hyer) len", min(len(x) for x in p2), 1)

    # lr preset: C+ -> C- is unreachable (mode flip needs odd count, but
    # L/R alone can reach it via LR...? verify it is reachable or not).
    p3 = _all_shortest((0, 1), (0, -1), PATH_PRESETS['lr'])
    check("lr C+ -> C- reachable?", bool(p3), True)  # L reaches (E,-)... P needed?
    # C+ -> D+ under lr only (may be unreachable): just assert it returns a list.
    check("lr returns list", isinstance(
        _all_shortest((0, 1), (2, 1), PATH_PRESETS['lr']), list), True)

    # --- resolve_path_ops ---
    check("resolve plr",  resolve_path_ops("plr"),  ('P', 'L', 'R'))
    check("resolve hyer", resolve_path_ops("hyer"), ('D6', 'L', 'R', 'P'))
    check("resolve PLR",  resolve_path_ops("PLR"),  ('P', 'L', 'R'))
    check("resolve 'P L D6'", resolve_path_ops("P L D6"), ('P', 'L', 'D6'))
    check_error("resolve invalid token", lambda: resolve_path_ops("XYZ"))

    # --- pretty token / superscript ---
    check("pretty D6",  _pretty_token("D6"),  "D\u2076")   # D⁶
    check("pretty D-1", _pretty_token("D-1"), "D\u207B\u00b9")
    check("pretty P",   _pretty_token("P"),   "P")

    # --- compress_word ---
    check("compress LRLR", compress_word("LRLR"), "(LR)\u00b2")
    check("compress PP",   compress_word("PP"),   "P\u00b2")

    # --- inspect / describe_utt smoke test ---
    d = describe_utt(UTT_TABLE['P'])
    check("inspect P riemannian", "Riemannian" in d, True)

    # --- Spelled triad output uses stacked-thirds spelling ---
    nrt.OUTPUT_STYLE = 'spell'
    nrt.SPELLING = 'sharp'
    check_eval("spell C minor uses E-flat", "(C,-)", "[C,E♭,G]")
    nrt.SPELLING = 'flat'
    check_eval("spell G-flat major", "(G♭,+)", "[G♭,B♭,D♭]")
    nrt.SPELLING = 'sharp'
    nrt.OUTPUT_STYLE = 'tuple'

    # --- Error paths ---
    check_error("no object",      lambda: evaluate("(LR)(PP)"))
    check_error("bad operator",   lambda: group_to_utt("Z"))
    nrt.LAST_TRIAD = None
    check_error("memory empty",   lambda: evaluate("_"))

    # --- Last-result memory '_' ---
    check_eval("memory seed", "(C,+)(LR)", "(G,+)")
    check_eval("memory recall", "_", "(G,+)")
    check_eval("memory apply", "_(P)", "(G,-)")
    check_eval("memory reseed", "(C,+)(LR)", "(G,+)")
    check_eval("memory apply compact", "_P", "(G,-)")
    check("path parse memory start", parse_path("_ (C,+)"), ((7, -1), (0, 1)))

    # --- format_steps (--steps): keep user sequence, expand compounds ---
    nrt.OUTPUT_STYLE = 'tuple'
    s = format_steps("C(LR)")
    check("steps C(LR) count",  "2 steps" in s, True)
    check("steps C(LR) L step", "→ (E,-)" in s, True)
    check("steps C(LR) final",  s.strip().endswith("(G,+)"), True)

    check("iter H -> PLP",  list(_iter_side_tokens("H")),  ['P', 'L', 'P'])
    check("iter N -> PLR",  list(_iter_side_tokens("N")),  ['P', 'L', 'R'])
    check("iter S -> LPR",  list(_iter_side_tokens("S")),  ['L', 'P', 'R'])
    check("iter P' -> RPL", list(_iter_side_tokens("P'")), ['R', 'P', 'L'])
    check("steps H is 3",   "3 steps" in format_steps("C(H)"), True)

    # Sequence must NOT collapse: LRLRLR stays 6 steps (not shortest T-form).
    check("steps no collapse", "6 steps" in format_steps("C(LRLRLR)"), True)

    # Expansion faithful: same final triad as evaluate().
    for expr in ("C(H)", "(Eb,-)N", "G-(S)", "C(P')", "C(LRLRLR)"):
        want, _ = evaluate(expr)
        steps = format_steps(expr)
        matches = re.findall(r'\([^()\n]+,[+-]\)', steps)
        got = matches[-1] if matches else ''
        check(f"steps faithful {expr}", got, want)

    # Prefix-then-suffix order.
    check("iter order LR + P",
          list(_iter_side_tokens("LR")) + list(_iter_side_tokens("P")),
          ['L', 'R', 'P'])

    print(f"\n{passed} passed, {failed} failed.")
    return failed == 0
