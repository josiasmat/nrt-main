import re

# --- Pitch-class tables ---
PC_TO_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
PC_TO_FLAT  = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

NOTE_TO_PC = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11,
}

# Full names of pitch classes (used for the spelled-out triad description).
NAME_SHARP = ['C', 'C-sharp', 'D', 'D-sharp', 'E', 'F',
              'F-sharp', 'G', 'G-sharp', 'A', 'A-sharp', 'B']
NAME_FLAT  = ['C', 'D-flat', 'D', 'E-flat', 'E', 'F',
              'G-flat', 'G', 'A-flat', 'A', 'B-flat', 'B']


_preferred_accidental = 'auto'  # 'auto', 'sharp', or 'flat'
_preferred_triad_spelling = 'auto'  # 'auto', 'short', or 'long'
_LETTERS = ['C', 'D', 'E', 'F', 'G', 'A', 'B']


class Note:
    """Class representing a musical note with a pitch class and optional accidental."""

    def __init__(self, pc, accidental=None, letter=None, name=None):
        self.pc = pc % 12
        self.accidental = accidental
        self.letter = letter
        self.name = name

    @classmethod
    def from_string(cls, s):
        """Convert a string like 'C', 'C#', 'Db' to a Note object."""
        s = _depretty(s.strip())
        if not s: raise ValueError("Empty note string")
        m = re.fullmatch(r'([A-Ga-g])([#b]*)', s)
        if not m:
            raise ValueError(f"Invalid note string: {s}")
        letter = m.group(1).upper()
        acc = m.group(2)
        pc = (NOTE_TO_PC[letter] + acc.count('#') - acc.count('b')) % 12
        if not acc:
            accidental = None
        elif '#' in acc and 'b' in acc:
            raise ValueError(f"Invalid mixed accidental string: {s}")
        else:
            accidental = 'sharp' if '#' in acc else 'flat'
        name = letter + acc
        return cls(pc, accidental, letter=letter, name=name)

    def __eq__(self, other):
        if isinstance(other, Note):
            return self.pc == other.pc
        return NotImplemented

    def __str__(self):
        if self.name is not None:
            return self.name
        if self.accidental == 'sharp':
            return PC_TO_SHARP[self.pc]
        if self.accidental == 'flat':
            return PC_TO_FLAT[self.pc]
        if _preferred_accidental == 'sharp':
            return PC_TO_SHARP[self.pc]
        if _preferred_accidental == 'flat':
            return PC_TO_FLAT[self.pc]
        return PC_TO_SHARP[self.pc] if self.pc == 6 \
                else PC_TO_FLAT[self.pc]

    def pretty(self, condition=True):
        """Return a pretty-printed version of the note, 
           using Unicode symbols for sharps and flats."""
        return str(self).replace('b', '♭').replace('#', '♯') if condition \
                else str(self)


# Minor mode specifiers for triads
MINOR_SPECIFIERS = ['-', 'm', 'min', 'minor']


def _depretty(note):
    return note.replace('♭', 'b').replace('♯', '#')


def set_preferred_accidental(value):
    if value not in ('auto', 'sharp', 'flat'):
        raise ValueError("preferred accidental must be 'auto', 'sharp', or 'flat'")
    global _preferred_accidental
    _preferred_accidental = value


def _accidental_suffix(letter, target_pc):
    natural_pc = NOTE_TO_PC[letter]
    diff = (target_pc - natural_pc) % 12
    if diff == 0:
        return ''
    if diff <= 6:
        return '#' * diff
    return 'b' * (12 - diff)


class Triad:
    """Class representing a major/minor triad, defined by its root and mode."""

    def __init__(self, root, mode, accidental=None):
        self._mode = mode
        if isinstance(root, Note):
            self._root = root
        elif isinstance(root, int):
            self._root = Note(root, accidental)
        elif isinstance(root, str):
            self._root = Note.from_string(root)
        else:
            raise TypeError(f"root must be an int, str, or Note, not {type(root).__name__}")

    @classmethod
    def from_string(cls, s):
        """Create a Triad from any documented object format in help.py."""
        text = _depretty(s.strip())
        if not text:
            raise ValueError("Invalid triad string: empty input")

        # Tuple forms: (C,+), (C,-), (C,M), (C,m)
        m = re.fullmatch(r'\(\s*([A-Ga-g](?:#|b)?)\s*,\s*([+\-Mm])\s*\)', text)
        if m:
            root = Note.from_string(m.group(1))
            mode = '+' if m.group(2) in ['+', 'M'] else '-'
            return cls(root, mode)

        # Spelled triads: [C,E,G], {C,Eb,G}, [c,e,g], {c,eb,g}
        m = re.fullmatch(
            r'([\[{])\s*([A-Ga-g](?:#|b)?)\s*,\s*([A-Ga-g](?:#|b)?)\s*,\s*([A-Ga-g](?:#|b)?)\s*([\]}])',
            text
        )
        if m and ((m.group(1) == '[' and m.group(5) == ']') or (m.group(1) == '{' and m.group(5) == '}')):
            root = Note.from_string(m.group(2))
            third = Note.from_string(m.group(3))
            fifth = Note.from_string(m.group(4))

            intervals = sorted([(third.pc - root.pc) % 12, (fifth.pc - root.pc) % 12])
            if intervals == [4, 7]:
                mode = '+'
            elif intervals == [3, 7]:
                mode = '-'
            else:
                raise ValueError(f"Invalid triad spelling: {s}")

            return cls(root, mode)

        # Optional wrapper for short/plain forms: (C), (c), (C+), (Cm), ...
        m = re.fullmatch(r'\(\s*([^(),]+)\s*\)', text)
        if m:
            text = m.group(1).strip()

        # Short/plain forms: C, c, C+, C-, CM, Cm
        m = re.fullmatch(r'([A-Ga-g](?:#|b)?)([A-Za-z+\-]*)', text)
        if not m:
            raise ValueError(f"Invalid triad string: {s}")

        root_token, mode_token = m.group(1), m.group(2)
        root = Note.from_string(root_token)
        if mode_token == '':
            mode = '+' if root_token[0].isupper() else '-'
        elif mode_token in ['+', 'M']:
            mode = '+'
        elif mode_token in MINOR_SPECIFIERS:
            mode = '-'
        else:
            raise ValueError(f"Invalid triad mode specifier: {mode_token}")

        return cls(root, mode)


    def root(self):
        """Return the root of the triad as a named note."""
        return self._root

    def mode(self):
        """Return the mode of the triad ('+' for major, '-' for minor)."""
        return self._mode

    def third(self):
        """Return the third of the triad as a named note."""
        interval = 4 if self._mode == '+' else 3
        target_pc = (self._root.pc + interval) % 12
        root_letter = self._root.letter or str(self._root)[0].upper()
        letter_idx = _LETTERS.index(root_letter)
        third_letter = _LETTERS[(letter_idx + 2) % 7]
        name = third_letter + _accidental_suffix(third_letter, target_pc)
        return Note.from_string(name)

    def fifth(self):
        """Return the fifth of the triad as a named note."""
        target_pc = (self._root.pc + 7) % 12
        root_letter = self._root.letter or str(self._root)[0].upper()
        letter_idx = _LETTERS.index(root_letter)
        fifth_letter = _LETTERS[(letter_idx + 4) % 7]
        name = fifth_letter + _accidental_suffix(fifth_letter, target_pc)
        return Note.from_string(name)

    def notes(self):
        """Return a tuple of the triad's notes in order: root, third, fifth."""
        return (self.root(), self.third(), self.fifth())
    

    def str_tuple(self, pretty=True):
        """Return a string representation of the triad as a tuple (root,mode)."""
        return f"({self.root().pretty(pretty)},{self.mode()})"

    def str_short_sign(self, pretty=True):
        """Return a string representation of the triad like 'C#+', 'Db-'."""
        return f"{self.root().pretty(pretty)}{self.mode()}"
    
    def str_short_mode(self, pretty=True):
        """Return a string representation of the triad like 'C#M', 'Dbm'."""
        return f"{self.root().pretty(pretty)}{'M' if self.mode() == '+' else 'm'}"
    
    def str_short_case(self, pretty=True):
        """Return a string representation of the triad like 'C#', 'db')."""
        return f"{self.root().pretty(pretty) if self.mode() == '+' else self.root().pretty(pretty).lower()}"

    def str_long(self, pretty=True):
        """Return a string representation of the triad like 'C# major', 'Db minor'."""
        return f"{self.root().pretty(pretty)} {'major' if self.mode() == '+' else 'minor'}"

    def str_spelled(self, lowercase=False, brackets='[]', pretty=True):
        """Return a string representation of the triad as a spelled-out list of notes."""
        notes = self.notes()
        if lowercase:
            notes_str = [note.pretty(pretty).lower() for note in notes]
        else:
            notes_str = [note.pretty(pretty) for note in notes]
        return f"{brackets[0]}{','.join(notes_str)}{brackets[1]}"

    def __str__(self):
        return self.str_tuple()

    def __repr__(self):
        return f"Triad(root={self._root}, mode={self._mode})"


def find_triads(s):
    """Return all triad objects found in the input string, left to right."""
    note = r'[A-Ga-g](?:[#b♯♭])?'
    candidate_re = re.compile(
        rf'''
        \(\s*{note}\s*,\s*[+\-Mm]\s*\) |
        [\[\{{]\s*{note}\s*,\s*{note}\s*,\s*{note}\s*[\]\}}] |
        \(\s*{note}(?:[+\-Mm]|min|minor)?\s*\) |
        {note}(?:[+\-Mm]|min|minor)?
        ''',
        re.VERBOSE
    )

    triads = []

    def _in_delimited(pos):
        depth_paren = s.count('(', 0, pos) - s.count(')', 0, pos)
        depth_brack = s.count('[', 0, pos) - s.count(']', 0, pos)
        depth_brace = s.count('{', 0, pos) - s.count('}', 0, pos)
        return depth_paren > 0 or depth_brack > 0 or depth_brace > 0

    for m in candidate_re.finditer(s):
        token = m.group(0)

        # Bare/root-suffix tokens should be isolated from surrounding words.
        if token and token[0].isalpha():
            before = s[m.start() - 1] if m.start() > 0 else ''
            after = s[m.end()] if m.end() < len(s) else ''
            if before.isalpha() or after.isalpha():
                continue
            if after.isdigit():
                continue
            if _in_delimited(m.start()):
                continue

        try:
            triads.append(Triad.from_string(token))
        except ValueError:
            # Candidate matched the lexer pattern but is not a valid triad object.
            continue

    return triads
