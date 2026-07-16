import re


PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")


def normalize_phone(phone):
    return phone.strip()


def is_valid_phone(phone):
    return bool(PHONE_PATTERN.fullmatch(phone))
