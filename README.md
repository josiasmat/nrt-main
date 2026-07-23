# Neo-Riemannian Transformation Evaluator (NRT)

A python script that reads and evaluates neo-riemannian expressions.

## Run

Download the script from:

https://github.com/josiasmat/nrt-main/releases/latest/download/nrt.pyz

and run inside a terminal with: `python nrt.pyz`.

Requires Python 3.6 or newer.

# How to use

NRT accepts expressions and commands.

An expression consists of one **OBJECT** (a triad) with **OPERATORS** applied to it.

Operators may appear before and/or after the object; they are applied left to
right (prefix first, then suffix). Spaces are ignored. Operators may be grouped
in parentheses, e.g. `(LR)` = L then R.

## Examples

    >>> C (LR)         apply L then R to the C major triad
    >>> (P) F#m        apply P to the C major triad
    >>> (D,+)(RP)      apply R then P to the D major triad
    >>> (Eb,-) S2 W1   apply S2 then W1 to the Eb minor triad
    >>> [G,Bb,D](D2)   apply D2 to the G minor triad
    >>> G- <+,2,10>    apply the UTT <+,2,10> to the G minor triad

## Object Formats

All examples denote the same C major/minor triads.

| Format | Notes |
|--------|-------|
| `C` `(C)` `c` `(c)` | plain: uppercase = major, lowercase `(c)` = minor |
| `C+` `(C+)` `C-` `(C-)` | root + mode suffix |
| `CM` `(CM)` `Cm` `(Cm)` | root + mode suffix (`M`/`+` = major, `m`/`-` = minor) |
| `(C,+)` `(C,-)` | root with polarity inside parentheses |
| `(C,M)` `(C,m)` | root with polarity inside parentheses |
| `[C,E,G]` `{C,Eb,G}` | spelled triad inside brackets or braces (parentheses are **NOT** accepted here) |
| `_` | last triad result from memory |

**Accidentals on input:** `#` = sharp, `b` = flat (e.g. `Eb`, `F#`).

## Operators

### Basic transformations

| Operator | Name |
|----------|------|
| `P` | Parallel |
| `L` | Leittonwechsel |
| `R` | Relative |

### Common compound transformations

| Operator | Name | Equivalent |
|----------|------|------------|
| `S` / `P'` | Slide | `LPR` / `RPL` |
| `N` / `L'` | Nebenverwandt | `PLR` / `RLP` |
| `R'` | R prime | `LRP` / `PRL` |
| `H` | Hexatonic pole | `PLP` |

### Parametrized operators

| Operator | Name | Definition |
|----------|------|------------|
| `D<n>` | Dominant | Transpose n fifths down |
| `T<n>` | Transposition | Transpose n semitones up |
| `I<n>` | Inversion | `⟨-, n, n⟩` (`I` alone = `I0` = `P`) |
| `S<n>` | Schritt (Hook) | `⟨+, n, -n⟩` (`S` with a digit; bare `S` = Slide) |
| `W<n>` | Wechsel (Hook) | `⟨-, -n, n⟩` (= `Sn o P`) |
| `<s,tp,tm>` | literal UTT | e.g. `<+,2,10>` or `<-,3,9>` |

### UTT Literals

`<s,tp,tm>` — a **Uniform Triadic Transformation** (Hook 2002).

- `s` = `+` (keep mode) or `-` (invert mode)
- `tp` = transposition applied to a major triad
- `tm` = transposition applied to a minor triad

**Example:** `<+,2,10>(C,+) -> (D,+)`

## Step-by-step output

    <expr> --follow
    
Decompose the expression, showing each operator applied one at a time 
(like `path:`). The user's sequence is kept; compounds (H, N, S, P', L', R') 
expand to P/L/R atomics.

**Examples:**

    C (LR) --follow
    (Gm)(H) --follow
    follow: C (LR)
    follow (Gm)(H)


## Inspection

    inspect: <ops>

Normalize a transformation (no object) into a single UTT `<s,tp,tm>` and show
its type, whether it is Riemannian, and its order. Respects the current
`mode:` (`lr`/`rl`).

**Examples:**

    inspect: PLR
    inspect: LR
    inspect: <+,2,10>PL

## Path discover

    path: <O1> <O2> [--ops SET]

Compute the shortest path between two triads `O1` and `O2`.

`SET` selects the atomics:

| SET | Atomic transformations |
|-----|------------|
| `plr` | P/L/R group (default) |
| `hyer` | adds Dominant D6 (P/L/R/D6) |
| `lr` | L/R only (may be unreachable) |

Or an explicit token list, e.g. `--ops PLD6`.

**Examples:**

    path: (C,+) (G,-)
    path --ops hyer (C,+) (G,+)
    path (C,+) (E,-) --ops lr

## Options

### Output Style

| Command | Effect |
|---------|--------|
| `out:input` | inherit style from the object (default) |
| `out:short` | show triad as a short string (e.g. `C+`) |
| `out:tuple` | show triad as a `(root,mode)` tuple (e.g. `(C,+)`) |
| `out:spell` | show triad as a spelled-out list of notes (e.g. `[C,E,G]`) |
| `out` | show current output style |

### Description in Output

| Command | Effect |
|---------|--------|
| `desc:on` | append a full description of the triad (e.g. "C major triad") |
| `desc:off` | omit the full description (default) |
| `desc` | show current description setting |

### Spelling Commands

Change how results are written.

| Command | Effect |
|---------|--------|
| `spell:sharp` | force sharps (e.g. `G#`) |
| `spell:flat` | force flats (e.g. `Ab`) |
| `spell:auto` | pick sharps/flats from the resulting root (conventional keys) |
| `spell:input` | inherit spelling from the object (default) |
| `spell` | show current spelling setting |

## Other Commands

| Command | Effect |
|---------|--------|
| `help` | show help text |
| `quit` / `exit` | leave the program |
