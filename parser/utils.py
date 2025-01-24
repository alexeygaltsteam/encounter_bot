import re


def extract_limit(text: str) -> int:
    match = re.search(r'\d+', text)
    if match:
        return int(match.group(0))
    return 0
