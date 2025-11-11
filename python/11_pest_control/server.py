def encode_u32(n: int) -> bytes:
    assert n >= 0 and n <= (2**32 - 1)
    return bytes([(n >> 24) % 256, (n >> 16) % 256, (n >> 8) % 256, n % 256])


def encode_str(s: str) -> bytes:
    return encode_u32(len(s)) + s.encode("utf-8")


def message_wrapper(message_type: bytes, contents: bytes) -> bytes:
    assert len(message_type) == 1
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
    return message_wrapper(b"\x51", encode_str(message))


def dial_authority_message(site: int) -> bytes:
    return message_wrapper(b"\x53", encode_u32(site))


def create_policy_message(species: str, action: bytes) -> bytes:
    assert len(action) == 1
    assert action == b"\x90" or action == b"\xa0"
    return message_wrapper(b"\x55", encode_str(species) + action)


def delete_policy_message(policy: int) -> bytes:
    return message_wrapper(b"\x56", encode_u32(policy))


def parse_u32(b: bytes, index: int) -> int:
    # convert 4 byte unsigned integer (u32) to the integer type
    assert len(b) >= index + 4
    return (b[index] << 24) + (b[index + 1] << 16) + (b[index + 2] << 8) + b[index + 3]


def parse_str(b: bytes, index: int) -> str:
    str_len = parse_u32(b, index)
    assert len(b) >= index + 4 + str_len
    return b[index + 4 : index + 4 + str_len].decode("utf-8")


def parse_array(
    b: bytes, index: int, spec: dict[str, str]
) -> list[dict[str, int | str]]:
    arr_len = parse_u32(b, index)
    index += 4
    arr = []
    for _ in range(arr_len):
        # parse element
        elem = {}
        for key, value in spec.items():
            if value == "u32":
                # parse u32
                int_val = parse_u32(b, index)
                index += 4
                elem[key] = int_val
            elif value == "str":
                # parse str
                str_val = parse_str(b, index)
                index += 4 + len(str_val)
                elem[key] = str_val
            else:
                raise Exception(f"Unknown spec type {value}")
        arr.append(elem)
    return arr


def parse_hello_message(b: bytes) -> dict[str, str | int]:
    index = 5
    protocol = parse_str(b, index)
    index += 4 + len(protocol)
    version = parse_u32(b, index)
    index += 4
    return {"protocol": protocol, "version": version}


def parse_error_message(b: bytes) -> dict[str, str]:
    index = 5
    message = parse_str(b, index)
    index += 4 + len(message)
    return {"message": message}


def parse_ok_message(b: bytes) -> dict:
    return {}


def parse_target_populations_message(b: bytes):
    index = 5
    site = parse_u32(b, index)
    index += 4
    populations = parse_array(b, index, {"species": "str", "min": "u32", "max": "u32"})
    return {"site": site, "populations": populations}


def parse_policy_result_message(b: bytes):
    index = 5
    policy = parse_u32(b, index)
    index += 4
    return {"policy": policy}


def parse_site_visit_message(b: bytes):
    index = 5
    site = parse_u32(b, index)
    index += 4
    populations = parse_array(b, index, {"species": "str", "count": "u32"})
    return {"site": site, "populations": populations}


def parse_message(b: bytes) -> dict:
    message_length = parse_u32(b, 1)
    print(f"{message_length=}")
    assert message_length == len(b)
    byte_sum = 0
    for val in b:
        byte_sum += val
    print(f"{byte_sum=} {byte_sum % 256 =}")
    if b[0] == 0x50:
        print("Hello")
    elif b[0] == 0x51:
        print("Error")
    elif b[0] == 0x52:
        print("OK")
    elif b[0] == 0x53:
        print("DialAuthority")
    elif b[0] == 0x54:
        print("TargetPopulations")
    elif b[0] == 0x55:
        print("CreatePolicy")
    elif b[0] == 0x56:
        print("DeletePolicy")
    elif b[0] == 0x57:
        print("PolicyResult")
    elif b[0] == 0x58:
        print("SiteVisit")
    else:
        raise Exception(f"Unrecognized message type {b[0]}")


if __name__ == "__main__":
    # parse_message(b"\x58\x00\x00\x00\x24")
    # parse_message(
    #     b"\x50\x00\x00\x00\x19\x00\x00\x00\x0b\x70\x65\x73\x74\x63\x6f\x6e\x74\x72\x6f\x6c\x00\x00\x00\x01\xce"
    # )
    print(" ".join(f"{b:02x}" for b in hello_message("pestcontrol", 1)))
