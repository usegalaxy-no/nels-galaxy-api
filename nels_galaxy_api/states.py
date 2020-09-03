import kbr.crypt_utils as crypt_utils


states = {}


def set(data: any) -> int:
    global states
    uuid = crypt_utils.create_uuid(5)
    states[uuid] = data
    return uuid


def get(uuid: str, purge: bool = False):
    global states

    if uuid not in states:
        return None

    data = states[uuid]
    if purge:
        del states[uuid]

    return data

