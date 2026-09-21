class CacheService:
    """
    Protocol-facing named cache service.

    Supported operations:
      create_cache
      remove_cache
      list_caches
      set
      get
      peek
      delete
      clear
      purge_expired
      save_state
      load_state
      status
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            CacheManager()
            if manager is None
            else manager
        )

    def handle(
        self,
        request,
    ):
        if not isinstance(
            request,
            ServiceRequest,
        ):
            raise TypeError(
                "request must be ServiceRequest"
            )

        if request.service != "cache_service":
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = request.operation

            if operation == "create_cache":
                cache = (
                    self.manager
                    .create_cache(
                        cache_id=self._required(
                            request.payload,
                            "cache_id",
                        ),
                        max_entries=request.payload.get(
                            "max_entries",
                            1024,
                        ),
                        default_ttl_seconds=request.payload.get(
                            "default_ttl_seconds"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "cache": (
                            cache.stats()
                        ),
                    },
                )

            if operation == "remove_cache":
                cache = (
                    self.manager
                    .remove_cache(
                        self._required(
                            request.payload,
                            "cache_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "removed_cache_id": (
                            cache.cache_id
                        ),
                    },
                )

            if operation == "list_caches":
                caches = (
                    self.manager
                    .list_caches(
                        now=request.payload.get(
                            "now"
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "caches": caches,
                        "count": len(
                            caches
                        ),
                    },
                )

            if operation == "set":
                result = (
                    self.manager
                    .set(
                        cache_id=self._required(
                            request.payload,
                            "cache_id",
                        ),
                        key=self._required(
                            request.payload,
                            "key",
                        ),
                        value=self._required(
                            request.payload,
                            "value",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                        ttl_seconds=request.payload.get(
                            "ttl_seconds"
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "set": result,
                    },
                )

            if operation in (
                "get",
                "peek",
            ):
                method = (
                    self.manager.get
                    if operation == "get"
                    else self.manager.peek
                )

                result = method(
                    cache_id=self._required(
                        request.payload,
                        "cache_id",
                    ),
                    key=self._required(
                        request.payload,
                        "key",
                    ),
                    now=self._required(
                        request.payload,
                        "now",
                    ),
                    default=request.payload.get(
                        "default"
                    ),
                )

                return self._success(
                    request,
                    {
                        "result": result,
                    },
                )

            if operation == "delete":
                result = (
                    self.manager
                    .delete(
                        cache_id=self._required(
                            request.payload,
                            "cache_id",
                        ),
                        key=self._required(
                            request.payload,
                            "key",
                        ),
                    )
                )

                return self._success(
                    request,
                    result,
                )

            if operation == "clear":
                result = (
                    self.manager
                    .clear(
                        self._required(
                            request.payload,
                            "cache_id",
                        )
                    )
                )

                return self._success(
                    request,
                    result,
                )

            if operation == "purge_expired":
                result = (
                    self.manager
                    .purge_expired(
                        cache_id=self._required(
                            request.payload,
                            "cache_id",
                        ),
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                    )
                )

                return self._success(
                    request,
                    result,
                )

            if operation == "save_state":
                info = (
                    self.manager
                    .save_state(
                        self._required(
                            request.payload,
                            "path",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "artifact": info,
                    },
                )

            if operation == "load_state":
                info = (
                    self.manager
                    .load_state_file(
                        self._required(
                            request.payload,
                            "path",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "status": info,
                    },
                )

            if operation == "status":
                return self._success(
                    request,
                    {
                        "status": (
                            self.manager
                            .status(
                                now=request.payload.get(
                                    "now"
                                )
                            )
                        ),
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                "Unsupported cache service operation",
            )

        except KeyError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(
                    error
                ),
            )

        except FileNotFoundError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(
                    error
                ),
            )

        except (
            ValueError,
            TypeError,
            IndexError,
        ) as error:
            return self._error(
                request,
                "INVALID_REQUEST",
                str(
                    error
                ),
            )

    def _required(
        self,
        payload,
        key,
    ):
        if key not in payload:
            raise ValueError(
                "payload requires "
                + key
            )

        return payload[
            key
        ]

    def _success(
        self,
        request,
        data,
    ):
        return (
            ServiceResponse
            .success_response(
                request,
                data=data,
            )
        )

    def _error(
        self,
        request,
        code,
        message,
    ):
        return (
            ServiceResponse
            .error_response(
                request,
                ProtocolError(
                    code=code,
                    message=message,
                    retryable=False,
                ),
            )
        )
