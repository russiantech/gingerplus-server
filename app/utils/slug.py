from slugify import slugify as _slugify


def slugify(text: str, max_length: int = 120) -> str:
    return _slugify(text, max_length=max_length) or "item"
