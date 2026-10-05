"""Autograd operation metadata and tensor-shape utilities.

This file uses no imports.  It expects the handwritten ``Tensor`` class from
``libs/core/math/tensor.py`` to exist in the runtime namespace.  SireLLM's
runtime loader will provide project-owned dependencies; no third-party module
is required.
"""


class Operation:
    """Small immutable description of an autograd operation."""

    def __init__(self, name, arity, category):
        self.name = str(name)
        self.arity = int(arity)
        self.category = str(category)

    def __repr__(self):
        return "Operation(name=" + repr(self.name) + ", arity=" + repr(self.arity) + ", category=" + repr(self.category) + ")"


ADD = Operation("add", 2, "elementwise")
SUBTRACT = Operation("subtract", 2, "elementwise")
MULTIPLY = Operation("multiply", 2, "elementwise")
DIVIDE = Operation("divide", 2, "elementwise")
POWER = Operation("power", 1, "elementwise")
MATMUL = Operation("matmul", 2, "linear_algebra")
SUM = Operation("sum", 1, "reduction")
MEAN = Operation("mean", 1, "reduction")
RESHAPE = Operation("reshape", 1, "view")
TRANSPOSE = Operation("transpose2d", 1, "view")
EXP = Operation("exp", 1, "activation")
LOG = Operation("log", 1, "activation")
TANH = Operation("tanh", 1, "activation")
SIGMOID = Operation("sigmoid", 1, "activation")
RELU = Operation("relu", 1, "activation")


def _shape_list(tensor):
    return [dimension for dimension in tensor.shape]


def _product(values):
    result = 1
    for value in values:
        result *= value
    return result


def _make_strides(shape):
    if len(shape) == 0:
        return []
    strides = [1] * len(shape)
    index = len(shape) - 2
    while index >= 0:
        strides[index] = strides[index + 1] * shape[index + 1]
        index -= 1
    return strides


def _unravel(flat_index, shape):
    if len(shape) == 0:
        return []
    strides = _make_strides(shape)
    coordinates = [0] * len(shape)
    remaining = flat_index
    axis = 0
    while axis < len(shape):
        stride = strides[axis]
        if stride == 0:
            coordinates[axis] = 0
        else:
            coordinates[axis] = remaining // stride
            remaining = remaining % stride
        axis += 1
    return coordinates


def _ravel(coordinates, shape):
    if len(shape) == 0:
        return 0
    strides = _make_strides(shape)
    result = 0
    axis = 0
    while axis < len(shape):
        result += coordinates[axis] * strides[axis]
        axis += 1
    return result


def _broadcast_shape(left_shape, right_shape):
    left = [value for value in left_shape]
    right = [value for value in right_shape]
    length = len(left) if len(left) >= len(right) else len(right)
    result = [1] * length

    offset = 1
    while offset <= length:
        left_dim = left[-offset] if offset <= len(left) else 1
        right_dim = right[-offset] if offset <= len(right) else 1
        if left_dim != right_dim and left_dim != 1 and right_dim != 1:
            raise ValueError("tensor shapes are not broadcast-compatible")
        result[-offset] = left_dim if left_dim >= right_dim else right_dim
        offset += 1
    return result


def _project_coordinate(output_coordinate, input_shape):
    if len(input_shape) == 0:
        return []
    offset = len(output_coordinate) - len(input_shape)
    projected = [0] * len(input_shape)
    axis = 0
    while axis < len(input_shape):
        coordinate = output_coordinate[offset + axis]
        projected[axis] = 0 if input_shape[axis] == 1 else coordinate
        axis += 1
    return projected


def _binary_tensor(left, right, mode):
    """Elementwise binary op with NumPy-style shape broadcasting."""
    output_shape = _broadcast_shape(left.shape, right.shape)
    output_size = _product(output_shape)
    left_values = left.flatten()
    right_values = right.flatten()
    left_shape = _shape_list(left)
    right_shape = _shape_list(right)

    if mode == "divide":
        for value in right_values:
            if value == 0:
                raise ZeroDivisionError("division by zero")

    if (
        "GPU_BACKEND" in globals()
        and GPU_BACKEND is not None
        and GPU_BACKEND.enabled()
        and output_size > 0
    ):
        values = GPU_BACKEND.binary_broadcast(
            left_values,
            left_shape,
            right_values,
            right_shape,
            output_shape,
            mode,
        )
        return Tensor(values, output_shape)

    values = [0.0] * output_size

    index = 0
    while index < output_size:
        out_coordinate = _unravel(index, output_shape)
        left_coordinate = _project_coordinate(out_coordinate, left_shape)
        right_coordinate = _project_coordinate(out_coordinate, right_shape)
        left_index = _ravel(left_coordinate, left_shape)
        right_index = _ravel(right_coordinate, right_shape)
        a = left_values[left_index]
        b = right_values[right_index]

        if mode == "add":
            value = a + b
        elif mode == "subtract":
            value = a - b
        elif mode == "multiply":
            value = a * b
        elif mode == "divide":
            if b == 0:
                raise ZeroDivisionError("division by zero")
            value = a / b
        else:
            raise ValueError("unsupported binary tensor operation")

        values[index] = value
        index += 1

    return Tensor(values, output_shape)


def _sum_to_shape(tensor, target_shape):
    """Reduce a broadcasted gradient back to a parent's original shape."""
    target = [value for value in target_shape]
    source_shape = _shape_list(tensor)
    if source_shape == target:
        return tensor.copy()

    # Validate that target could have broadcast to source.
    _broadcast_shape(target, source_shape)

    source_values = tensor.flatten()
    target_size = _product(target)
    output = [0.0] * target_size
    index = 0
    while index < len(source_values):
        source_coordinate = _unravel(index, source_shape)
        target_coordinate = _project_coordinate(source_coordinate, target)
        target_index = _ravel(target_coordinate, target)
        output[target_index] += source_values[index]
        index += 1
    return Tensor(output, target)


def _add_gradients(left, right):
    if left.shape != right.shape:
        raise ValueError("gradient shapes must match")
    return left.add(right)


def _ones_like(tensor):
    return Tensor.ones(_shape_list(tensor))


def _zeros_like(tensor):
    return Tensor.zeros(_shape_list(tensor))


def _scalar_tensor(value):
    return Tensor([float(value)], [])
