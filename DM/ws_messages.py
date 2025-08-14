# DM_refactored/socket.py

def get_init_message(device_code: str) -> dict:
    """Returns the DEVICE:HELLO message."""
    return {
        "type": "DEVICE:HELLO",
        "payload": {
            "code": device_code
        }
    }

def get_status_message(device_id: str, mileage: float) -> dict:
    """Returns the DRIVING:STATUS message."""
    return {
        "type": "DRIVING:STATUS",
        "payload": {
            "deviceId": device_id,
            "mileage": mileage
        }
    }

def get_stop_message(device_id: str, msg_gaze: dict, msg_lds: dict) -> dict:
    """Returns the DRIVING:STOP message."""
    return {
        "type": "DRIVING:STOP",
        "payload": {
            "deviceId": device_id,
            "mileage": msg_lds.get("mileage", 0),
            "bias": msg_lds.get("bias", 0),
            "headway": msg_lds.get("headway", 0),
            "left": msg_gaze.get("left", 0),
            "right": msg_gaze.get("right", 0),
            "front": msg_gaze.get("front", 0)
        }
    }
