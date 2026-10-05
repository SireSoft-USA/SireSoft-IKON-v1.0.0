class CrossEntropyLoss:
    """
    Stable categorical cross-entropy for next-token language modeling.

    Logits:
      [classes]
      [sequence, classes]
      [batch, sequence, classes]
      ... any rank >= 1

    Targets must match logits.shape[:-1].

    Features:
      - reduction: mean / sum / none
      - ignore_index for padding/unwanted target positions
      - optional label smoothing
      - direct stable log-sum-exp computation
      - handwritten analytical backward pass
    """

    def __init__(
        self,
        reduction="mean",
        ignore_index=-100,
        label_smoothing=0.0,
    ):
        if reduction not in ("mean", "sum", "none"):
            raise ValueError(
                "reduction must be mean, sum, or none"
            )

        if ignore_index is not None and not isinstance(
            ignore_index,
            int,
        ):
            raise TypeError(
                "ignore_index must be int or None"
            )

        if not isinstance(
            label_smoothing,
            (int, float),
        ):
            raise TypeError(
                "label_smoothing must be numeric"
            )

        if (
            label_smoothing < 0.0
            or label_smoothing >= 1.0
        ):
            raise ValueError(
                "label_smoothing must satisfy 0 <= value < 1"
            )

        self.reduction = reduction
        self.ignore_index = ignore_index
        self.label_smoothing = float(
            label_smoothing
        )

    def __call__(self, logits, targets):
        return self.forward(logits, targets)

    def forward(self, logits, targets):
        x = Value.ensure(logits)

        if x.ndim < 1:
            raise ValueError(
                "cross entropy logits require rank >= 1"
            )

        classes = x.shape[-1]

        if classes <= 1:
            raise ValueError(
                "cross entropy requires at least two classes"
            )

        target_values, target_shape = (
            self._flatten_targets(targets)
        )

        expected_shape = list(x.shape[:-1])

        # Rank-1 logits correspond to one scalar target.
        if x.ndim == 1:
            expected_shape = []

        if target_shape != expected_shape:
            raise ValueError(
                "target shape "
                + repr(tuple(target_shape))
                + " does not match logits prefix shape "
                + repr(tuple(expected_shape))
            )

        rows = x.size // classes

        if len(target_values) != rows:
            raise ValueError(
                "target count does not match logits rows"
            )

        row_index = 0
        while row_index < len(target_values):
            target = target_values[row_index]
            ignored = (
                self.ignore_index is not None
                and target == self.ignore_index
            )
            if not ignored and (target < 0 or target >= classes):
                raise IndexError(
                    "target class out of range at row " + str(row_index)
                )
            row_index += 1

        if (
            "GPU_BACKEND" in globals()
            and GPU_BACKEND is not None
            and GPU_BACKEND.enabled()
        ):
            return self._forward_cuda(
                x, target_values, expected_shape, rows, classes
            )

        source = x.data.flatten()

        probabilities = [0.0] * x.size
        row_losses = [0.0] * rows
        active = [False] * rows
        active_count = 0

        row = 0

        while row < rows:
            target = target_values[row]

            if (
                self.ignore_index is not None
                and target == self.ignore_index
            ):
                row_losses[row] = 0.0
                row += 1
                continue

            if target < 0 or target >= classes:
                raise IndexError(
                    "target class out of range at row "
                    + str(row)
                )

            active[row] = True
            active_count += 1

            start = row * classes

            maximum = source[start]

            class_index = 1
            while class_index < classes:
                candidate = source[
                    start + class_index
                ]

                if candidate > maximum:
                    maximum = candidate

                class_index += 1

            denominator = 0.0
            exponentials = [0.0] * classes

            class_index = 0
            while class_index < classes:
                e = exp(
                    source[start + class_index]
                    - maximum
                )

                exponentials[class_index] = e
                denominator += e
                class_index += 1

            log_denominator = log(denominator)
            log_sum_exp = (
                maximum + log_denominator
            )

            class_index = 0
            average_negative_log_probability = 0.0

            while class_index < classes:
                probability = (
                    exponentials[class_index]
                    / denominator
                )

                probabilities[
                    start + class_index
                ] = probability

                log_probability = (
                    source[start + class_index]
                    - log_sum_exp
                )

                average_negative_log_probability += (
                    -log_probability
                )

                class_index += 1

            average_negative_log_probability /= classes

            target_negative_log_probability = -(
                source[start + target]
                - log_sum_exp
            )

            smoothing = self.label_smoothing

            row_losses[row] = (
                (1.0 - smoothing)
                * target_negative_log_probability
                + smoothing
                * average_negative_log_probability
            )

            row += 1

        if self.reduction == "none":
            if x.ndim == 1:
                output_tensor = Tensor(
                    [row_losses[0]],
                    [],
                )
            else:
                output_tensor = Tensor(
                    row_losses,
                    expected_shape,
                )

        elif self.reduction == "sum":
            total = 0.0

            row = 0
            while row < rows:
                total += row_losses[row]
                row += 1

            output_tensor = Tensor(
                [total],
                [],
            )

        else:
            if active_count == 0:
                raise ValueError(
                    "mean cross entropy has no active targets"
                )

            total = 0.0

            row = 0
            while row < rows:
                total += row_losses[row]
                row += 1

            output_tensor = Tensor(
                [total / active_count],
                [],
            )

        out = Value(
            output_tensor,
            requires_grad=x.requires_grad,
            _children=[x],
            _op="cross_entropy",
        )

        def _backward():
            if not x.requires_grad:
                return

            gradient = [0.0] * x.size

            if self.reduction == "none":
                upstream_rows = out.grad.flatten()

                if x.ndim == 1:
                    upstream_rows = [
                        upstream_rows[0]
                    ]
            else:
                upstream_scalar = (
                    out.grad.flatten()[0]
                )
                upstream_rows = None

            row_index = 0

            while row_index < rows:
                if not active[row_index]:
                    row_index += 1
                    continue

                target = target_values[
                    row_index
                ]

                if self.reduction == "none":
                    upstream = upstream_rows[
                        row_index
                    ]

                elif self.reduction == "sum":
                    upstream = upstream_scalar

                else:
                    upstream = (
                        upstream_scalar
                        / active_count
                    )

                start = (
                    row_index * classes
                )

                smoothing = (
                    self.label_smoothing
                )

                class_index = 0

                while class_index < classes:
                    target_probability = (
                        smoothing / classes
                    )

                    if class_index == target:
                        target_probability += (
                            1.0 - smoothing
                        )

                    gradient[
                        start + class_index
                    ] = (
                        probabilities[
                            start + class_index
                        ]
                        - target_probability
                    ) * upstream

                    class_index += 1

                row_index += 1

            x._accumulate(
                Tensor(
                    gradient,
                    [
                        dimension
                        for dimension
                        in x.shape
                    ],
                )
            )

        out._backward = _backward
        return out

    def _forward_cuda(self, x, target_values, expected_shape, rows, classes):
        ignore_index = (
            self.ignore_index
            if self.ignore_index is not None
            else -2147483647
        )
        probabilities, row_losses, active = GPU_BACKEND.cross_entropy_forward(
            x.data.flatten(),
            target_values,
            rows,
            classes,
            ignore_index,
            self.label_smoothing,
        )
        active_count = 0
        total = 0.0
        row = 0
        while row < rows:
            if active[row]:
                active_count += 1
            total += row_losses[row]
            row += 1

        if self.reduction == "none":
            if x.ndim == 1:
                output_tensor = Tensor([row_losses[0]], [])
            else:
                output_tensor = Tensor(row_losses, expected_shape)
        elif self.reduction == "sum":
            output_tensor = Tensor([total], [])
        else:
            if active_count == 0:
                raise ValueError("mean cross entropy has no active targets")
            output_tensor = Tensor([total / active_count], [])

        out = Value(
            output_tensor,
            requires_grad=x.requires_grad,
            _children=[x],
            _op="cross_entropy",
        )

        def _backward():
            if not x.requires_grad:
                return
            if self.reduction == "none":
                upstream_rows = out.grad.flatten()
                if x.ndim == 1:
                    upstream_rows = [upstream_rows[0]]
            else:
                upstream_rows = [out.grad.flatten()[0]]

            gradient = GPU_BACKEND.cross_entropy_backward(
                probabilities,
                target_values,
                active,
                upstream_rows,
                rows,
                classes,
                self.label_smoothing,
                active_count,
                self.reduction,
            )
            x._accumulate(
                Tensor(gradient, [dimension for dimension in x.shape])
            )

        out._backward = _backward
        return out

    def _flatten_targets(self, targets):
        flat = []
        shape = self._infer_targets(
            targets,
            flat,
        )

        return flat, shape

    def _infer_targets(self, data, flat):
        if isinstance(data, int):
            flat.append(data)
            return []

        if not isinstance(
            data,
            (list, tuple),
        ):
            raise TypeError(
                "targets must contain integer class IDs"
            )

        if len(data) == 0:
            return [0]

        expected = None

        for item in data:
            child_shape = self._infer_targets(
                item,
                flat,
            )

            if expected is None:
                expected = child_shape

            elif child_shape != expected:
                raise ValueError(
                    "targets must be rectangular"
                )

        return [len(data)] + expected
