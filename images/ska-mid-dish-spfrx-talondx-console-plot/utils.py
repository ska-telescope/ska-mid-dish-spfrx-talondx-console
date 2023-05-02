def mac_to_int(ether: str) -> int:
    return int(
        ether.replace(":", ""), 16
    )  # convert to hex and interpret as integer.


def ip_to_int(inet: str) -> int:
    return sum(
        [int(v) << (i * 8) for i, v in enumerate(reversed(inet.split(".")))]
    )
