class AuthCrypto:
    """
    Pure-Python SHA-256, HMAC-SHA256, and PBKDF2-HMAC-SHA256 primitives.

    This exists to satisfy SireLLM's from-scratch educational constraint.
    Production authentication should use platform-vetted cryptographic
    implementations and a dedicated password KDF such as Argon2id/scrypt.
    """

    MASK32 = 0xFFFFFFFF

    INITIAL = (
        0x6A09E667,
        0xBB67AE85,
        0x3C6EF372,
        0xA54FF53A,
        0x510E527F,
        0x9B05688C,
        0x1F83D9AB,
        0x5BE0CD19,
    )

    K = (
        0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5,
        0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5,
        0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3,
        0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174,
        0xE49B69C1, 0xEFBE4786, 0x0FC19DC6, 0x240CA1CC,
        0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
        0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7,
        0xC6E00BF3, 0xD5A79147, 0x06CA6351, 0x14292967,
        0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13,
        0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85,
        0xA2BFE8A1, 0xA81A664B, 0xC24B8B70, 0xC76C51A3,
        0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
        0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5,
        0x391C0CB3, 0x4ED8AA4A, 0x5B9CCA4F, 0x682E6FF3,
        0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208,
        0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
    )

    HEX = "0123456789abcdef"

    def sha256(self, data):
        data = self._bytes(data)

        bit_length = len(data) * 8

        padded = bytearray(data)
        padded.append(0x80)

        while (
            len(padded) % 64
        ) != 56:
            padded.append(0)

        shift = 56

        while shift >= 0:
            padded.append(
                (
                    bit_length
                    >> shift
                )
                & 0xFF
            )
            shift -= 8

        state = list(
            self.INITIAL
        )

        offset = 0

        while offset < len(padded):
            block = padded[
                offset:
                offset + 64
            ]

            schedule = [
                0
            ] * 64

            index = 0

            while index < 16:
                base = index * 4

                schedule[index] = (
                    (block[base] << 24)
                    | (block[base + 1] << 16)
                    | (block[base + 2] << 8)
                    | block[base + 3]
                )

                index += 1

            while index < 64:
                value_15 = schedule[
                    index - 15
                ]

                value_2 = schedule[
                    index - 2
                ]

                s0 = (
                    self._rotr(
                        value_15,
                        7,
                    )
                    ^ self._rotr(
                        value_15,
                        18,
                    )
                    ^ (
                        value_15
                        >> 3
                    )
                )

                s1 = (
                    self._rotr(
                        value_2,
                        17,
                    )
                    ^ self._rotr(
                        value_2,
                        19,
                    )
                    ^ (
                        value_2
                        >> 10
                    )
                )

                schedule[index] = (
                    schedule[
                        index - 16
                    ]
                    + s0
                    + schedule[
                        index - 7
                    ]
                    + s1
                ) & self.MASK32

                index += 1

            a, b, c, d, e, f, g, h = state

            index = 0

            while index < 64:
                upper_e = (
                    self._rotr(
                        e,
                        6,
                    )
                    ^ self._rotr(
                        e,
                        11,
                    )
                    ^ self._rotr(
                        e,
                        25,
                    )
                )

                choose = (
                    (e & f)
                    ^ (
                        (~e)
                        & g
                    )
                ) & self.MASK32

                temp1 = (
                    h
                    + upper_e
                    + choose
                    + self.K[
                        index
                    ]
                    + schedule[
                        index
                    ]
                ) & self.MASK32

                upper_a = (
                    self._rotr(
                        a,
                        2,
                    )
                    ^ self._rotr(
                        a,
                        13,
                    )
                    ^ self._rotr(
                        a,
                        22,
                    )
                )

                majority = (
                    (a & b)
                    ^ (a & c)
                    ^ (b & c)
                ) & self.MASK32

                temp2 = (
                    upper_a
                    + majority
                ) & self.MASK32

                h = g
                g = f
                f = e
                e = (
                    d
                    + temp1
                ) & self.MASK32
                d = c
                c = b
                b = a
                a = (
                    temp1
                    + temp2
                ) & self.MASK32

                index += 1

            state[0] = (
                state[0]
                + a
            ) & self.MASK32

            state[1] = (
                state[1]
                + b
            ) & self.MASK32

            state[2] = (
                state[2]
                + c
            ) & self.MASK32

            state[3] = (
                state[3]
                + d
            ) & self.MASK32

            state[4] = (
                state[4]
                + e
            ) & self.MASK32

            state[5] = (
                state[5]
                + f
            ) & self.MASK32

            state[6] = (
                state[6]
                + g
            ) & self.MASK32

            state[7] = (
                state[7]
                + h
            ) & self.MASK32

            offset += 64

        digest = bytearray()

        for value in state:
            shift = 24

            while shift >= 0:
                digest.append(
                    (
                        value
                        >> shift
                    )
                    & 0xFF
                )

                shift -= 8

        return bytes(
            digest
        )

    def hmac_sha256(
        self,
        key,
        data,
    ):
        key = self._bytes(
            key
        )

        data = self._bytes(
            data
        )

        if len(key) > 64:
            key = self.sha256(
                key
            )

        if len(key) < 64:
            key = (
                key
                + bytes(
                    [0] * (
                        64
                        - len(key)
                    )
                )
            )

        inner = bytearray()
        outer = bytearray()

        index = 0

        while index < 64:
            inner.append(
                key[index]
                ^ 0x36
            )

            outer.append(
                key[index]
                ^ 0x5C
            )

            index += 1

        inner.extend(
            data
        )

        inner_digest = (
            self.sha256(
                bytes(
                    inner
                )
            )
        )

        outer.extend(
            inner_digest
        )

        return self.sha256(
            bytes(
                outer
            )
        )

    def pbkdf2_hmac_sha256(
        self,
        password,
        salt,
        iterations,
        length=32,
    ):
        password = self._bytes(
            password
        )

        salt = self._bytes(
            salt
        )

        if (
            not isinstance(
                iterations,
                int,
            )
            or iterations <= 0
        ):
            raise ValueError(
                "iterations must be positive int"
            )

        if (
            not isinstance(
                length,
                int,
            )
            or length <= 0
        ):
            raise ValueError(
                "length must be positive int"
            )

        blocks = (
            length
            + 31
        ) // 32

        output = bytearray()

        block_index = 1

        while block_index <= blocks:
            counter = self._int32_be(
                block_index
            )

            u = self.hmac_sha256(
                password,
                salt + counter,
            )

            result = bytearray(
                u
            )

            round_index = 1

            while round_index < iterations:
                u = self.hmac_sha256(
                    password,
                    u,
                )

                index = 0

                while index < len(
                    result
                ):
                    result[index] ^= (
                        u[index]
                    )

                    index += 1

                round_index += 1

            output.extend(
                result
            )

            block_index += 1

        return bytes(
            output[
                :length
            ]
        )

    def constant_time_equal(
        self,
        left,
        right,
    ):
        left = self._bytes(
            left
        )

        right = self._bytes(
            right
        )

        difference = (
            len(left)
            ^ len(right)
        )

        length = max(
            len(left),
            len(right),
        )

        index = 0

        while index < length:
            left_byte = (
                left[index]
                if index < len(
                    left
                )
                else 0
            )

            right_byte = (
                right[index]
                if index < len(
                    right
                )
                else 0
            )

            difference |= (
                left_byte
                ^ right_byte
            )

            index += 1

        return difference == 0

    def to_hex(
        self,
        data,
    ):
        data = self._bytes(
            data
        )

        result = ""

        for value in data:
            result += self.HEX[
                value
                >> 4
            ]

            result += self.HEX[
                value
                & 0x0F
            ]

        return result

    def from_hex(
        self,
        value,
    ):
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "hex value must be str"
            )

        if len(value) % 2 != 0:
            raise ValueError(
                "hex value must have even length"
            )

        output = bytearray()

        index = 0

        while index < len(value):
            high = self._hex_value(
                value[index]
            )

            low = self._hex_value(
                value[
                    index + 1
                ]
            )

            output.append(
                (
                    high
                    << 4
                )
                | low
            )

            index += 2

        return bytes(
            output
        )

    def encode_text_hex(
        self,
        value,
    ):
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "value must be str"
            )

        return self.to_hex(
            value.encode(
                "utf-8"
            )
        )

    def decode_text_hex(
        self,
        value,
    ):
        return (
            self.from_hex(
                value
            )
            .decode(
                "utf-8"
            )
        )

    def _rotr(
        self,
        value,
        count,
    ):
        value &= self.MASK32

        return (
            (
                value
                >> count
            )
            | (
                value
                << (
                    32
                    - count
                )
            )
        ) & self.MASK32

    def _int32_be(
        self,
        value,
    ):
        return bytes([
            (
                value
                >> 24
            )
            & 0xFF,
            (
                value
                >> 16
            )
            & 0xFF,
            (
                value
                >> 8
            )
            & 0xFF,
            value
            & 0xFF,
        ])

    def _bytes(
        self,
        value,
    ):
        if isinstance(
            value,
            bytes,
        ):
            return value

        if isinstance(
            value,
            bytearray,
        ):
            return bytes(
                value
            )

        if isinstance(
            value,
            str,
        ):
            return value.encode(
                "utf-8"
            )

        raise TypeError(
            "value must be bytes-like or str"
        )

    def _hex_value(
        self,
        char,
    ):
        if (
            char >= "0"
            and char <= "9"
        ):
            return ord(
                char
            ) - ord(
                "0"
            )

        lower = char.lower()

        if (
            lower >= "a"
            and lower <= "f"
        ):
            return (
                ord(
                    lower
                )
                - ord(
                    "a"
                )
                + 10
            )

        raise ValueError(
            "invalid hex character"
        )
