class GradientClipResult:
    def __init__(self, norm_before, norm_after, scale):
        self.norm_before = norm_before
        self.norm_after = norm_after
        self.scale = scale

    def to_dict(self):
        return {
            "norm_before": self.norm_before,
            "norm_after": self.norm_after,
            "scale": self.scale,
        }


class GlobalNormClipper:
    """
    Clips the global L2 norm across all trainable parameter gradients.
    """

    def __init__(self, max_norm, epsilon=1e-12):
        if not isinstance(max_norm, (int, float)) or max_norm <= 0.0:
            raise ValueError("max_norm must be > 0")
        if not isinstance(epsilon, (int, float)) or epsilon <= 0.0:
            raise ValueError("epsilon must be > 0")

        self.max_norm = float(max_norm)
        self.epsilon = float(epsilon)

    def norm(self, parameters):
        params = self._collect(parameters)
        total = 0.0

        for parameter in params:
            if not getattr(parameter, "requires_grad", True):
                continue

            values = parameter.grad.flatten()
            if (
                "GPU_BACKEND" in globals()
                and GPU_BACKEND is not None
                and GPU_BACKEND.enabled()
                and len(values) > 0
            ):
                total += GPU_BACKEND.sum_squares(values)
            else:
                for value in values:
                    total += value * value

        return sqrt(total)

    def clip(self, parameters):
        params = self._collect(parameters)
        norm_before = self.norm(params)

        if norm_before <= self.max_norm or norm_before == 0.0:
            return GradientClipResult(
                norm_before,
                norm_before,
                1.0,
            )

        scale = self.max_norm / (
            norm_before + self.epsilon
        )

        for parameter in params:
            if not getattr(parameter, "requires_grad", True):
                continue

            values = parameter.grad.flatten()
            if (
                "GPU_BACKEND" in globals()
                and GPU_BACKEND is not None
                and GPU_BACKEND.enabled()
                and len(values) > 0
            ):
                clipped = GPU_BACKEND.scale(values, scale)
            else:
                clipped = []
                for value in values:
                    clipped.append(value * scale)

            parameter.grad = Tensor(
                clipped,
                [dimension for dimension in parameter.shape],
            )

        norm_after = self.norm(params)

        return GradientClipResult(
            norm_before,
            norm_after,
            scale,
        )

    def _collect(self, parameters):
        if hasattr(parameters, "parameters") and callable(parameters.parameters):
            parameters = parameters.parameters()

        if not isinstance(parameters, (list, tuple)):
            parameters = list(parameters)

        return list(parameters)


class ValueClipper:
    """
    Clips every gradient element independently to [-max_abs, max_abs].
    """

    def __init__(self, max_abs):
        if not isinstance(max_abs, (int, float)) or max_abs <= 0.0:
            raise ValueError("max_abs must be > 0")

        self.max_abs = float(max_abs)

    def clip(self, parameters):
        if hasattr(parameters, "parameters") and callable(parameters.parameters):
            parameters = parameters.parameters()

        parameters = list(parameters)

        total_before = 0.0
        total_after = 0.0

        for parameter in parameters:
            if not getattr(parameter, "requires_grad", True):
                continue

            source = parameter.grad.flatten()
            clipped = []

            for value in source:
                total_before += value * value

                if value > self.max_abs:
                    new_value = self.max_abs
                elif value < -self.max_abs:
                    new_value = -self.max_abs
                else:
                    new_value = value

                clipped.append(new_value)
                total_after += new_value * new_value

            parameter.grad = Tensor(
                clipped,
                [dimension for dimension in parameter.shape],
            )

        norm_before = sqrt(total_before)
        norm_after = sqrt(total_after)

        if norm_before == 0.0:
            scale = 1.0
        else:
            scale = norm_after / norm_before

        return GradientClipResult(
            norm_before,
            norm_after,
            scale,
        )
