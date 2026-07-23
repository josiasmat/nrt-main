HELP_TEXT = """\
An expression consists of one OBJECT (a triad) with OPERATORS applied to it.
Operators may appear before and/or after the object; they are applied left to
right (prefix first, then suffix). Spaces are ignored. Operators may be 
grouped in parentheses, e.g. (LR) = L then R.

EXAMPLES:
  >>> C (LR)         apply L then R to the C major triad
  >>> (P) F#m        apply the UTT <+,2,10> to the C major triad
  >>> (D,+)(RP)      apply R then P to the D major triad
  >>> (Eb,-) S2 W1   apply S2 then W1 to the Eb minor triad
  >>> [G,Bb,D](D2)   apply D2 to the G minor triad
  >>> G- <+,2,10>    apply the UTT <+,2,10> to the G minor triad

OBJECT FORMATS (all examples denote the same C major/minor triads):
  C  (C)  c  (c)     plain: uppercase = major, lowercase (c) = minor
  C+ (C+) C- (C-)
  CM (CM) Cm (Cm)    root + mode suffix (M/+ = major, m/- = minor)
  (C,+)   (C,-)
  (C,M)   (C,m)      root with polarity inside parentheses
  [C,E,G] {C,Eb,G}   spelled triad inside brackets or braces
  [c,e,g] {c,eb,g}   (parentheses are NOT accepted here)
  _                  last triad result (memory)

  Accidentals on input: '#' = sharp, 'b' = flat  (e.g. Eb, F#).

OPERATORS:
  P      Parallel
  L      Leittonwechsel
  R      Relative

  S      Slide           = LPR / RPL / P'
  N      Nebenverwandt   = PLR / RLP / L'
  H      Hexatonic pole  = PLP

  P'     P prime         = LPR / RPL / S
  L'     L prime         = PLR / RLP / N
  R'     R prime         = LRP / PRL

  D<n>   Dominant        Transpose n fifths down
  T<n>   Transposition   Transpose n semitones up
  I<n>   Inversion       ⟨-, n, n⟩     (I alone = I0 = P)

  S<n>   Schritt (Hook)  ⟨+, n, -n⟩    (S with a digit; bare S = Slide)
  W<n>   Wechsel (Hook)  ⟨-, -n, n⟩    (= Sn o P)

  <s,tp,tm>      literal UTT, e.g. <+,2,10> or <-,3,9>

UTT LITERALS:
  <s,tp,tm>    a Uniform Triadic Transformation (Hook 2002).
               s  = + (keep mode) or - (invert mode)
               tp = transposition applied to a major triad
               tm = transposition applied to a minor triad
               Example: <+,2,10>(C,+) -> (D,+)

STEP-BY-STEP OUTPUT:
  <expr> --follow  decompose the expression, showing each operator applied
                   one at a time (like path:). The user's sequence is kept;
                   compounds (H, N, S, P', L', R') expand to P/L/R generators.
                   Example:  C (LR) --follow    (Gm)(H) --follow
  follow:<expr>    same as above (also accepts: follow <expr>)

INSPECTION:
  inspect:<ops>  normalize a transformation (no object) into a single
                 UTT <s,tp,tm> and show its type, whether it is
                 Riemannian, and its order.
                 Respects the current mode:(lr/rl).
                 Examples:  inspect:PLR    inspect:LR    inspect:<+,2,10>PL

P/L/R PATH:
  path:<O1><O2> [--ops SET]
                 compute the shortest path between two triads O1 and O2.
                 SET selects the generators:
                   plr   P/L/R group       (default)
                   hyer  adds Dominant D1  (P/L/R/D⁶)
                   lr    L/R only
                 or an explicit token list, e.g. --ops PLD⁶
                 Examples:
                   path: (C,+) (G,-)
                   path --ops hyer (C,+) (G,+)
                   path (C,+) (E,-) --ops lr

OUTPUT STYLE:
  out:input      inherit style from the object (default)
  out:short      show triad as a short string (e.g. C+)
  out:tuple      show triad as a (root,mode) tuple (e.g. (C,+))
  out:spell      show triad as a spelled-out list of notes (e.g. [C,E,G])
  out            show current output style

DESCRIPTION IN OUTPUT:
  desc:on        append a full description of the triad (e.g. "C major triad")
  desc:off       omit the full description (default)
  desc           show current description setting

SPELLING COMMANDS (change how results are written):
  spell:sharp    force sharps  (e.g. G#)
  spell:flat     force flats   (e.g. Ab)
  spell:auto     pick sharps/flats from the resulting root (conventional keys)
  spell:input    inherit spelling from the object (default)
  spell          show current spelling setting

OTHER COMMANDS:
  help           show this help
  quit / exit    leave the program
"""


def print_help():
    """Print the help text."""
    print(HELP_TEXT)
