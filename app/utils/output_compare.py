def outputs_match(actual: str, expected: str) -> bool:
    """
    Compare two output strings leniently but deterministically.

    Rules:
    - Normalize CRLF → LF throughout.
    - Strip trailing whitespace from every line.
    - Strip leading and trailing blank lines from the full output.
    - Compare the resulting line sequences exactly.

    No fuzzy matching or token-based comparison is performed.
    """

    def normalize(text: str) -> list[str]:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in text.split("\n")]
        # Remove leading blank lines
        while lines and lines[0] == "":
            lines.pop(0)
        # Remove trailing blank lines
        while lines and lines[-1] == "":
            lines.pop()
        return lines

    return normalize(actual) == normalize(expected)
