import uuid
import time
import secrets
from sqlalchemy import Uuid as SAUuid
from sqlalchemy.dialects.postgresql import UUID as PgUUID


def generate_uuid7() -> uuid.UUID:
    """Generate a UUID version 7 (time-ordered) per RFC 9562.

    Layout:
      Bits  0-47:  unixts (ms timestamp, big-endian)
      Bits 48-51:  version (0b0111 = 7)
      Bits 52-63:  rand_a (12 random bits)
      Bits 64-65:  variant (0b10)
      Bits 66-127: rand_b (62 random bits)
    """
    timestamp_ms = int(time.time() * 1000)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)

    value = (
        (timestamp_ms << 80)
        | (0x7 << 76)
        | (rand_a << 64)
        | (0x2 << 62)
        | rand_b
    )
    return uuid.UUID(int=value)
