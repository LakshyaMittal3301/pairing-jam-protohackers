def encode_u32(n: int) -> bytes:
    assert 0 <= n <= (2**32 - 1), f"u32 out of range: {n}"
    return bytes([(n >> 24) % 256, (n >> 16) % 256, (n >> 8) % 256, n % 256])


def encode_str(s: str) -> bytes:
    return encode_u32(len(s)) + s.encode("utf-8")


def message_wrapper(message_type: bytes, contents: bytes) -> bytes:
    assert len(message_type) == 1, (
        f"message_type must be 1 byte, got {len(message_type)}"
    )
    message_len = len(contents) + 1 + 4 + 1
    message = message_type + encode_u32(message_len) + contents
    checksum = 0
    for val in message:
        checksum -= val
    checksum %= 256
    return message + bytes([checksum])


def hello_message(protocol: str, version: int) -> bytes:
    return message_wrapper(b"\x50", encode_str(protocol) + encode_u32(version))


def error_message(message: str) -> bytes:
    print(f"{message=}")
    return message_wrapper(b"\x51", encode_str(message))


def dial_authority_message(site: int) -> bytes:
    return message_wrapper(b"\x53", encode_u32(site))


def create_policy_message(species: str, action: bytes) -> bytes:
    assert len(action) == 1, f"action must be 1 byte, got {len(action)}"
    assert action in (b"\x90", b"\xa0"), f"action must be 0x90 or 0xA0, got {action!r}"
    return message_wrapper(b"\x55", encode_str(species) + action)


def delete_policy_message(policy: int) -> bytes:
    return message_wrapper(b"\x56", encode_u32(policy))


def parse_u32(b: bytes, index: int) -> tuple[int, int]:
    # convert 4 byte unsigned integer (u32) to the integer type
    assert len(b) >= index + 4, (
        f"buffer too small for u32 at index {index}: len={len(b)}"
    )
    return (b[index] << 24) + (b[index + 1] << 16) + (b[index + 2] << 8) + b[
        index + 3
    ], index + 4


def parse_str(b: bytes, index: int) -> tuple[str, int]:
    str_len, index = parse_u32(b, index)
    assert len(b) >= index + str_len, (
        f"buffer too small for string len {str_len} at index {index}: len={len(b)}"
    )
    return b[index : index + str_len].decode("utf-8"), index + str_len


def parse_array(
    b: bytes, index: int, spec: dict[str, str]
) -> tuple[list[dict[str, int | str]], int]:
    arr_len, index = parse_u32(b, index)
    arr = []
    for _ in range(arr_len):
        # parse element
        elem = {}
        for key, value in spec.items():
            if value == "u32":
                # parse u32
                int_val, index = parse_u32(b, index)
                elem[key] = int_val
            elif value == "str":
                # parse str
                str_val, index = parse_str(b, index)
                elem[key] = str_val
            else:
                raise Exception(f"Unknown spec type {value}")
        arr.append(elem)
    return arr, index


def parse_hello_message(b: bytes) -> dict[str, str | int]:
    index = 5
    protocol, index = parse_str(b, index)
    version, index = parse_u32(b, index)
    assert index + 1 == len(b)
    return {"protocol": protocol, "version": version}


def parse_error_message(b: bytes) -> dict[str, str]:
    index = 5
    message, index = parse_str(b, index)
    assert index + 1 == len(b)
    return {"message": message}


def parse_ok_message(b: bytes) -> dict:
    index = 5
    assert index + 1 == len(b)
    return {}


def parse_target_populations_message(b: bytes):
    index = 5
    site, index = parse_u32(b, index)
    populations, index = parse_array(
        b, index, {"species": "str", "min": "u32", "max": "u32"}
    )
    assert index + 1 == len(b)
    return {"site": site, "populations": populations}


def parse_policy_result_message(b: bytes):
    index = 5
    policy, index = parse_u32(b, index)
    assert index + 1 == len(b)
    return {"policy": policy}


def parse_site_visit_message(b: bytes):
    index = 5
    site, index = parse_u32(b, index)
    populations, index = parse_array(b, index, {"species": "str", "count": "u32"})
    assert index + 1 == len(b)
    return {"site": site, "populations": populations}
