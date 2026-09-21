class AuthManager:
    """
    Stateful identity/session manager.

    Runtime time is supplied explicitly as integer seconds. This keeps the core
    deterministic and avoids hidden clock dependencies.
    """

    def __init__(
        self,
        server_secret,
        password_iterations=4096,
        min_password_length=8,
        max_failed_attempts=5,
        permission_policy=None,
        crypto=None,
    ):
        if (
            not isinstance(
                password_iterations,
                int,
            )
            or password_iterations <= 0
        ):
            raise ValueError(
                "password_iterations must be positive int"
            )

        if (
            not isinstance(
                min_password_length,
                int,
            )
            or min_password_length <= 0
        ):
            raise ValueError(
                "min_password_length must be positive int"
            )

        if (
            not isinstance(
                max_failed_attempts,
                int,
            )
            or max_failed_attempts <= 0
        ):
            raise ValueError(
                "max_failed_attempts must be positive int"
            )

        self.crypto = (
            AuthCrypto()
            if crypto is None
            else crypto
        )

        self.token_codec = (
            TokenCodec(
                self.crypto,
                server_secret,
            )
        )

        self.server_secret = (
            server_secret
            .encode(
                "utf-8"
            )
        )

        self.password_iterations = (
            password_iterations
        )

        self.min_password_length = (
            min_password_length
        )

        self.max_failed_attempts = (
            max_failed_attempts
        )

        self.permission_policy = (
            PermissionPolicy()
            if permission_policy is None
            else permission_policy
        )

        self._users = {}
        self._usernames = {}
        self._user_order = []
        self._sessions = {}
        self._session_order = []
        self._salt_sequence = 0
        self._session_sequence = 0

    def create_user(
        self,
        user_id,
        username,
        password,
        roles=None,
        metadata=None,
    ):
        if user_id in self._users:
            raise ValueError(
                "user_id already exists: "
                + str(user_id)
            )

        normalized_username = self._normalize_username(
            username
        )

        if normalized_username in self._usernames:
            raise ValueError(
                "username already exists"
            )

        self._validate_password(
            password
        )

        if roles is None:
            roles = [
                "user",
            ]

        self._validate_roles(
            roles
        )

        password_record = (
            self._password_record(
                user_id,
                password,
                credential_version=1,
            )
        )

        user = UserAccount(
            user_id=user_id,
            username=username,
            password_record=(
                password_record
            ),
            roles=roles,
            metadata=metadata,
        )

        self._users[
            user_id
        ] = user

        self._usernames[
            normalized_username
        ] = user_id

        self._user_order.append(
            user_id
        )

        return user

    def get_user(
        self,
        user_id,
    ):
        if user_id not in self._users:
            raise KeyError(
                "user not found: "
                + str(user_id)
            )

        return self._users[
            user_id
        ]

    def find_user(
        self,
        identifier,
    ):
        if identifier in self._users:
            return self._users[
                identifier
            ]

        if not isinstance(
            identifier,
            str,
        ):
            raise TypeError(
                "identifier must be str"
            )

        normalized = (
            self._normalize_username(
                identifier
            )
        )

        if normalized not in self._usernames:
            raise KeyError(
                "user not found: "
                + identifier
            )

        return self._users[
            self._usernames[
                normalized
            ]
        ]

    def list_users(
        self,
    ):
        return [
            self._users[
                user_id
            ].public_dict()
            for user_id
            in self._user_order
        ]

    def authenticate(
        self,
        identifier,
        password,
        now,
        ttl_seconds=3600,
    ):
        user = self.find_user(
            identifier
        )

        self._validate_now(
            now
        )

        if (
            not isinstance(
                ttl_seconds,
                int,
            )
            or ttl_seconds <= 0
        ):
            raise ValueError(
                "ttl_seconds must be positive int"
            )

        if not user.active():
            raise PermissionError(
                "user account is not active"
            )

        if not self._verify_password(
            user,
            password,
        ):
            user.failed_attempts += 1

            if (
                user.failed_attempts
                >= self.max_failed_attempts
            ):
                user.lock()

            raise PermissionError(
                "invalid credentials"
            )

        user.failed_attempts = 0

        self._session_sequence += 1

        session_id = (
            self._derive_session_id(
                user,
                now,
                self._session_sequence,
            )
        )

        nonce = (
            self._derive_nonce(
                user,
                now,
                self._session_sequence,
            )
        )

        expires_at = (
            int(now)
            + ttl_seconds
        )

        token = (
            self.token_codec
            .issue(
                session_id=session_id,
                user_id=user.user_id,
                username=user.username,
                roles=user.roles,
                credential_version=(
                    user.credential_version
                ),
                issued_at=int(now),
                expires_at=expires_at,
                nonce_text=nonce,
            )
        )

        token_digest = (
            self.crypto
            .to_hex(
                self.crypto
                .sha256(
                    token.encode(
                        "utf-8"
                    )
                )
            )
        )

        session = SessionRecord(
            session_id=session_id,
            user_id=user.user_id,
            username=user.username,
            roles=user.roles,
            issued_at=int(now),
            expires_at=expires_at,
            credential_version=(
                user.credential_version
            ),
            token_digest_hex=(
                token_digest
            ),
        )

        self._sessions[
            session_id
        ] = session

        self._session_order.append(
            session_id
        )

        return {
            "token": token,
            "session": (
                session.public_dict()
            ),
            "principal": (
                self._principal(
                    user,
                    session,
                )
            ),
        }

    def verify_token(
        self,
        token,
        now,
    ):
        self._validate_now(
            now
        )

        claims = (
            self.token_codec
            .decode_and_verify(
                token
            )
        )

        if int(now) >= int(
            claims[
                "expires_at"
            ]
        ):
            raise PermissionError(
                "authentication token expired"
            )

        session_id = claims[
            "session_id"
        ]

        if session_id not in self._sessions:
            raise PermissionError(
                "authentication session not found"
            )

        session = self._sessions[
            session_id
        ]

        if session.revoked:
            raise PermissionError(
                "authentication session revoked"
            )

        if not session.active(
            now
        ):
            raise PermissionError(
                "authentication session expired"
            )

        supplied_digest = (
            self.crypto
            .to_hex(
                self.crypto
                .sha256(
                    token.encode(
                        "utf-8"
                    )
                )
            )
        )

        if not self.crypto.constant_time_equal(
            self.crypto.from_hex(
                supplied_digest
            ),
            self.crypto.from_hex(
                session.token_digest_hex
            ),
        ):
            raise PermissionError(
                "authentication session token mismatch"
            )

        user = self.get_user(
            session.user_id
        )

        if not user.active():
            raise PermissionError(
                "user account is not active"
            )

        if (
            claims[
                "credential_version"
            ]
            != user.credential_version
        ):
            raise PermissionError(
                "authentication token invalidated by credential change"
            )

        if claims[
            "roles"
        ] != user.roles:
            raise PermissionError(
                "authentication token roles no longer current"
            )

        return self._principal(
            user,
            session,
        )

    def revoke_token(
        self,
        token,
        now,
    ):
        principal = (
            self.verify_token(
                token,
                now,
            )
        )

        session = self._sessions[
            principal[
                "session_id"
            ]
        ]

        session.revoked = True

        return (
            session.public_dict()
        )

    def revoke_user_sessions(
        self,
        user_id,
    ):
        self.get_user(
            user_id
        )

        count = 0

        for session_id in self._session_order:
            session = self._sessions[
                session_id
            ]

            if (
                session.user_id
                == user_id
                and not session.revoked
            ):
                session.revoked = True
                count += 1

        return {
            "user_id": user_id,
            "revoked_sessions": count,
        }

    def change_password(
        self,
        user_id,
        current_password,
        new_password,
    ):
        user = self.get_user(
            user_id
        )

        if not self._verify_password(
            user,
            current_password,
        ):
            raise PermissionError(
                "current password is invalid"
            )

        self._validate_password(
            new_password
        )

        user.credential_version += 1

        user.password_record = (
            self._password_record(
                user.user_id,
                new_password,
                credential_version=(
                    user.credential_version
                ),
            )
        )

        user.failed_attempts = 0

        self.revoke_user_sessions(
            user_id
        )

        return user.public_dict()

    def disable_user(
        self,
        user_id,
    ):
        user = self.get_user(
            user_id
        )

        user.disable()

        self.revoke_user_sessions(
            user_id
        )

        return user.public_dict()

    def enable_user(
        self,
        user_id,
    ):
        user = self.get_user(
            user_id
        )

        user.enable()

        return user.public_dict()

    def grant_role(
        self,
        user_id,
        role,
    ):
        user = self.get_user(
            user_id
        )

        self._validate_roles([
            role,
        ])

        if role not in user.roles:
            user.roles.append(
                role
            )

            self.revoke_user_sessions(
                user_id
            )

        return user.public_dict()

    def revoke_role(
        self,
        user_id,
        role,
    ):
        user = self.get_user(
            user_id
        )

        user.roles = [
            existing
            for existing in user.roles
            if existing != role
        ]

        self.revoke_user_sessions(
            user_id
        )

        return user.public_dict()

    def authorize(
        self,
        principal,
        permission,
    ):
        if not isinstance(
            principal,
            dict,
        ):
            raise TypeError(
                "principal must be dict"
            )

        roles = principal.get(
            "roles",
            [],
        )

        return {
            "permission": permission,
            "allowed": (
                self.permission_policy
                .allowed(
                    roles,
                    permission,
                )
            ),
            "roles": list(
                roles
            ),
        }

    def status(
        self,
    ):
        active_users = 0
        disabled_users = 0
        locked_users = 0
        active_sessions = 0
        revoked_sessions = 0

        for user_id in self._user_order:
            user = self._users[
                user_id
            ]

            if user.status == "active":
                active_users += 1

            elif user.status == "disabled":
                disabled_users += 1

            elif user.status == "locked":
                locked_users += 1

        for session_id in self._session_order:
            session = self._sessions[
                session_id
            ]

            if session.revoked:
                revoked_sessions += 1
            else:
                active_sessions += 1

        return {
            "ready": True,
            "users": len(
                self._user_order
            ),
            "active_users": active_users,
            "disabled_users": disabled_users,
            "locked_users": locked_users,
            "sessions": len(
                self._session_order
            ),
            "active_sessions": (
                active_sessions
            ),
            "revoked_sessions": (
                revoked_sessions
            ),
            "password_kdf": (
                "PBKDF2-HMAC-SHA256"
            ),
            "password_iterations": (
                self.password_iterations
            ),
            "permission_roles": (
                self.permission_policy
                .to_dict()
            ),
            "crypto_implementation": (
                "pure_python_educational"
            ),
        }

    def _password_record(
        self,
        user_id,
        password,
        credential_version,
    ):
        self._salt_sequence += 1

        salt_material = (
            "password-salt|"
            + user_id
            + "|"
            + str(
                credential_version
            )
            + "|"
            + str(
                self._salt_sequence
            )
        )

        salt = (
            self.crypto
            .hmac_sha256(
                self.server_secret,
                salt_material.encode(
                    "utf-8"
                ),
            )[
                :16
            ]
        )

        digest = (
            self.crypto
            .pbkdf2_hmac_sha256(
                password,
                salt,
                self.password_iterations,
                length=32,
            )
        )

        return PasswordRecord(
            salt_hex=(
                self.crypto
                .to_hex(
                    salt
                )
            ),
            digest_hex=(
                self.crypto
                .to_hex(
                    digest
                )
            ),
            iterations=(
                self.password_iterations
            ),
        )

    def _verify_password(
        self,
        user,
        password,
    ):
        if not isinstance(
            password,
            str,
        ):
            return False

        record = (
            user.password_record
        )

        salt = self.crypto.from_hex(
            record.salt_hex
        )

        digest = (
            self.crypto
            .pbkdf2_hmac_sha256(
                password,
                salt,
                record.iterations,
                length=32,
            )
        )

        expected = (
            self.crypto
            .from_hex(
                record.digest_hex
            )
        )

        return self.crypto.constant_time_equal(
            digest,
            expected,
        )

    def _derive_session_id(
        self,
        user,
        now,
        sequence,
    ):
        material = (
            "session-id|"
            + user.user_id
            + "|"
            + str(
                int(now)
            )
            + "|"
            + str(
                sequence
            )
        )

        return (
            self.crypto
            .to_hex(
                self.crypto
                .hmac_sha256(
                    self.server_secret,
                    material.encode(
                        "utf-8"
                    ),
                )[
                    :16
                ]
            )
        )

    def _derive_nonce(
        self,
        user,
        now,
        sequence,
    ):
        material = (
            "session-nonce|"
            + user.user_id
            + "|"
            + str(
                int(now)
            )
            + "|"
            + str(
                sequence
            )
        )

        return (
            self.crypto
            .to_hex(
                self.crypto
                .hmac_sha256(
                    self.server_secret,
                    material.encode(
                        "utf-8"
                    ),
                )[
                    :12
                ]
            )
        )

    def _principal(
        self,
        user,
        session,
    ):
        return {
            "user_id": user.user_id,
            "username": user.username,
            "roles": list(
                user.roles
            ),
            "permissions": (
                self.permission_policy
                .permissions_for_roles(
                    user.roles
                )
            ),
            "session_id": (
                session.session_id
            ),
            "issued_at": (
                session.issued_at
            ),
            "expires_at": (
                session.expires_at
            ),
        }

    def _validate_password(
        self,
        password,
    ):
        if not isinstance(
            password,
            str,
        ):
            raise TypeError(
                "password must be str"
            )

        if len(password) < (
            self.min_password_length
        ):
            raise ValueError(
                "password does not meet minimum length"
            )

    def _validate_roles(
        self,
        roles,
    ):
        if not isinstance(
            roles,
            (list, tuple),
        ):
            raise TypeError(
                "roles must be list/tuple"
            )

        for role in roles:
            if not self.permission_policy.role_exists(
                role
            ):
                raise ValueError(
                    "unknown role: "
                    + str(role)
                )

    def _validate_now(
        self,
        now,
    ):
        if not isinstance(
            now,
            int,
        ):
            raise TypeError(
                "now must be integer seconds"
            )

        if now < 0:
            raise ValueError(
                "now must be non-negative"
            )

    def _normalize_username(
        self,
        username,
    ):
        if not isinstance(
            username,
            str,
        ) or username == "":
            raise ValueError(
                "username must be non-empty str"
            )

        return username.strip().lower()
