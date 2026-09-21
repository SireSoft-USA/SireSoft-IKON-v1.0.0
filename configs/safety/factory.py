class SafetyConfigFactory:
    def build_patterns(self, config):
        if not isinstance(
            config,
            SafetyConfig,
        ):
            raise TypeError(
                "config must be SafetyConfig"
            )

        SafetyConfigValidator().require_valid(
            config
        )

        patterns = SafetyPatterns()

        if config.replace_default_rules:
            patterns.prompt_injection_patterns = []
            patterns.secret_patterns = []

        existing_codes = {}

        for phrase, code, severity in (
            patterns.prompt_injection_patterns
        ):
            existing_codes[code] = True

        for phrase, code, severity in (
            patterns.secret_patterns
        ):
            existing_codes[code] = True

        for rule in config.enabled_rules():
            if rule.code in existing_codes:
                raise ValueError(
                    "configured safety rule code conflicts with active rule: "
                    + rule.code
                )

            record = (
                rule.phrase,
                rule.code,
                rule.severity,
            )

            if (
                rule.category
                == "prompt_injection"
            ):
                patterns.prompt_injection_patterns.append(
                    record
                )
            else:
                patterns.secret_patterns.append(
                    record
                )

            existing_codes[rule.code] = True

        return patterns

    def build_engine(self, config):
        patterns = self.build_patterns(
            config
        )

        return GuardrailEngine(
            input_guard=InputGuard(
                patterns=patterns,
                max_characters=(
                    config.limits.input_characters
                ),
            ),
            context_guard=ContextGuard(
                patterns=patterns,
                max_characters=(
                    config.limits.context_characters
                ),
            ),
            output_guard=OutputGuard(
                patterns=patterns,
                max_characters=(
                    config.limits.output_characters
                ),
            ),
        )

    def build_manager(self, config):
        return GuardrailServiceManager(
            engine=self.build_engine(
                config
            )
        )

    def build_service(self, config):
        return GuardrailService(
            manager=self.build_manager(
                config
            )
        )
