import hashlib
import hmac
import struct
from base64 import b32decode
from unittest import TestCase

from src.login import Totp

# 16 base32 characters = 80 bits, the size of the secrets Microsoft issues
SHORT_SECRET = "JBSWY3DPEHPK3PXP"


def referenceTotp(secret: str, at: int, step: int = 30, digits: int = 6) -> str:
    """RFC 6238 / RFC 4226 computed without pyotp."""
    digest = hmac.new(
        b32decode(secret), struct.pack(">Q", at // step), hashlib.sha1
    ).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % 10**digits).zfill(digits)


class TestTotp(TestCase):
    def test_a_80_bit_secret_is_accepted(self):
        self.assertEqual(len(b32decode(SHORT_SECRET)) * 8, 80)

        self.assertEqual(len(Totp(SHORT_SECRET).now()), 6)

    def test_codes_match_the_rfc_algorithm_for_a_short_secret(self):
        for at in (59, 1_111_111_109, 1_793_000_000):
            with self.subTest(at=at):
                self.assertEqual(Totp(SHORT_SECRET).at(at), referenceTotp(SHORT_SECRET, at))

    def test_codes_match_the_rfc_6238_vector_for_a_long_secret(self):
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # b"12345678901234567890"

        self.assertEqual(Totp(secret, digits=8).at(59), "94287082")

    def test_the_secret_may_be_typed_in_lowercase(self):
        self.assertEqual(Totp(SHORT_SECRET.lower()).at(59), Totp(SHORT_SECRET).at(59))
