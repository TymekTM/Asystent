class PortAudioError(Exception):
    pass

_default_device = [0, 0]

class _Default:
    device = _default_device

def query_devices():
    return []

default = _Default()
