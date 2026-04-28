from app.utils.response import not_implemented_response


async def get_user_devices(upn: str) -> dict:
    # TODO: GET /users/{upn}/registeredDevices
    # Requires: Directory.Read.All
    return not_implemented_response("get_user_devices", "GET /users/{upn}/registeredDevices — needs Directory.Read.All")


async def detect_device_problems(upn: str) -> dict:
    # TODO: GET /users/{upn}/registeredDevices, check complianceState and lastSyncDateTime
    return not_implemented_response("detect_device_problems", "GET /users/{upn}/registeredDevices — check complianceState and lastSyncDateTime")
