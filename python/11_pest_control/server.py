from messages import *


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
