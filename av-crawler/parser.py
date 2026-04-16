import re

PATTERN = re.compile(r"([A-Z]+)-(\d+)")


def parse_code(code):
    match = PATTERN.match(code)
    if not match:
        return None

    prefix, number = match.groups()

    return {
        "raw": code,
        "prefix": prefix,
        "number": int(number)
    }