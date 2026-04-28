from mcp_msteams.utils.sanitization import mask_upn, mask_token, sanitize_log_value


def test_mask_upn_replaces_local_part():
    assert mask_upn("john.doe@contoso.com") == "u***@contoso.com"


def test_mask_upn_preserves_domain():
    result = mask_upn("admin@teams.example.org")
    assert result == "u***@teams.example.org"


def test_mask_upn_no_match_unchanged():
    assert mask_upn("no-email-here") == "no-email-here"


def test_mask_token_replaces_jwt():
    jwt = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signature"
    result = mask_token(f"Bearer {jwt}")
    assert "[TOKEN]" in result
    assert "eyJ" not in result


def test_sanitize_log_value_masks_both():
    value = "user@corp.com eyJhbGc.payload.sig"
    result = sanitize_log_value(value)
    assert "u***@corp.com" in result
    assert "[TOKEN]" in result
