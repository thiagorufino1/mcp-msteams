import re

_JWT_RE = re.compile(r'eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]*')
_UPN_RE = re.compile(r'(\S+)@(\S+\.\S+)')


def mask_upn(value: str) -> str:
    return _UPN_RE.sub(lambda m: f"u***@{m.group(2)}", value)


def mask_token(value: str) -> str:
    return _JWT_RE.sub("[TOKEN]", value)


def sanitize_log_value(value: str) -> str:
    return mask_upn(mask_token(str(value)))
