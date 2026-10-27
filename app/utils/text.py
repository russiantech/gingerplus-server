import re


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_phone(phone: str | None) -> str | None:
    """Normalise Nigerian numbers to +234XXXXXXXXXX where possible."""
    if not phone:
        return phone
    digits = re.sub(r"[^\d+]", "", phone)
    if digits.startswith("+"):
        return digits
    if digits.startswith("234"):
        return "+" + digits
    if digits.startswith("0") and len(digits) == 11:
        return "+234" + digits[1:]
    return digits


def whatsapp_link(number: str, message: str = "") -> str:
    from urllib.parse import quote
    n = re.sub(r"\D", "", number)
    return f"https://wa.me/{n}" + (f"?text={quote(message)}" if message else "")
