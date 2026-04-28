from app.utils.response import not_implemented_response


async def get_voice_configuration(upn: str) -> dict:
    # TODO: GET /users/{upn} with businessPhones + assignedLicenses + TeamsCallingPolicy
    return not_implemented_response("get_voice_configuration", "GET /users/{upn} with phone fields + calling policies")


async def validate_voice_routing(upn: str) -> dict:
    # TODO: GET /users/{upn}/teamwork — check TeamsCallingPolicy + voice routing policy
    return not_implemented_response("validate_voice_routing", "GET /users/{upn}/teamwork — check TeamsCallingPolicy + voice routing policy")


async def detect_voice_misconfiguration(upn: str) -> dict:
    # TODO: Cross-check TeamsCallingPolicy, DialPlan, VoiceRoutingPolicy for conflicts
    return not_implemented_response("detect_voice_misconfiguration", "Cross-check TeamsCallingPolicy, DialPlan, VoiceRoutingPolicy assignments")
