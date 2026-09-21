class SessionRecord:
    def __init__(
        self,
        session_id,
        user_id,
        username,
        roles,
        issued_at,
        expires_at,
        credential_version,
        token_digest_hex,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.username = username
        self.roles = list(
            roles
        )
        self.issued_at = int(
            issued_at
        )
        self.expires_at = int(
            expires_at
        )
        self.credential_version = int(
            credential_version
        )
        self.token_digest_hex = (
            token_digest_hex
        )
        self.revoked = False

    def active(
        self,
        now,
    ):
        return (
            not self.revoked
            and int(
                now
            ) < self.expires_at
        )

    def public_dict(
        self,
    ):
        return {
            "session_id": (
                self.session_id
            ),
            "user_id": (
                self.user_id
            ),
            "username": (
                self.username
            ),
            "roles": list(
                self.roles
            ),
            "issued_at": (
                self.issued_at
            ),
            "expires_at": (
                self.expires_at
            ),
            "credential_version": (
                self.credential_version
            ),
            "revoked": (
                self.revoked
            ),
        }


class TokenCodec:
    PREFIX = "sllm1"

    def __init__(
        self,
        crypto,
        server_secret,
    ):
        if not isinstance(
            crypto,
            AuthCrypto,
        ):
            raise TypeError(
                "crypto must be AuthCrypto"
            )

        if not isinstance(
            server_secret,
            str,
        ) or len(
            server_secret
        ) < 16:
            raise ValueError(
                "server_secret must be at least 16 characters"
            )

        self.crypto = crypto
        self.server_secret = (
            server_secret
            .encode(
                "utf-8"
            )
        )

    def issue(
        self,
        session_id,
        user_id,
        username,
        roles,
        credential_version,
        issued_at,
        expires_at,
        nonce_text,
    ):
        if expires_at <= issued_at:
            raise ValueError(
                "expires_at must be greater than issued_at"
            )

        role_text = ",".join(
            roles
        )

        fields = [
            self.PREFIX,
            self.crypto.encode_text_hex(
                session_id
            ),
            self.crypto.encode_text_hex(
                user_id
            ),
            self.crypto.encode_text_hex(
                username
            ),
            self.crypto.encode_text_hex(
                role_text
            ),
            str(
                int(
                    credential_version
                )
            ),
            str(
                int(
                    issued_at
                )
            ),
            str(
                int(
                    expires_at
                )
            ),
            self.crypto.encode_text_hex(
                nonce_text
            ),
        ]

        body = ".".join(
            fields
        )

        signature = (
            self.crypto
            .to_hex(
                self.crypto
                .hmac_sha256(
                    self.server_secret,
                    body.encode(
                        "utf-8"
                    ),
                )
            )
        )

        return (
            body
            + "."
            + signature
        )

    def decode_and_verify(
        self,
        token,
    ):
        if not isinstance(
            token,
            str,
        ) or token == "":
            raise ValueError(
                "token must be non-empty str"
            )

        parts = token.split(
            "."
        )

        if len(parts) != 10:
            raise ValueError(
                "invalid authentication token field count"
            )

        if parts[0] != self.PREFIX:
            raise ValueError(
                "invalid authentication token prefix"
            )

        body = ".".join(
            parts[
                :9
            ]
        )

        expected = (
            self.crypto
            .hmac_sha256(
                self.server_secret,
                body.encode(
                    "utf-8"
                ),
            )
        )

        supplied = (
            self.crypto
            .from_hex(
                parts[9]
            )
        )

        if not self.crypto.constant_time_equal(
            expected,
            supplied,
        ):
            raise ValueError(
                "authentication token signature mismatch"
            )

        role_text = (
            self.crypto
            .decode_text_hex(
                parts[4]
            )
        )

        roles = []

        if role_text != "":
            roles = role_text.split(
                ","
            )

        return {
            "session_id": (
                self.crypto
                .decode_text_hex(
                    parts[1]
                )
            ),
            "user_id": (
                self.crypto
                .decode_text_hex(
                    parts[2]
                )
            ),
            "username": (
                self.crypto
                .decode_text_hex(
                    parts[3]
                )
            ),
            "roles": roles,
            "credential_version": int(
                parts[5]
            ),
            "issued_at": int(
                parts[6]
            ),
            "expires_at": int(
                parts[7]
            ),
            "nonce": (
                self.crypto
                .decode_text_hex(
                    parts[8]
                )
            ),
        }
