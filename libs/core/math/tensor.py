"""N-dimensional dense tensor backed by a flat Python list.

This is the first general tensor container for SireLLM. Automatic
differentiation is deliberately kept out of this layer and will be added in
``libs/core/autograd``.
"""


class Tensor:
    def __init__(self, data, shape=None):
        if isinstance(data, Tensor):
            self._data = data._data[:]
            self._shape = data._shape[:]
            self._strides = data._strides[:]
            return

        if shape is None:
            flat, inferred_shape = self._flatten_and_infer(data)
            self._data = [float(value) for value in flat]
            self._shape = inferred_shape
        else:
            self._shape = self._validate_shape(shape)
            expected = self._product(self._shape)
            flat = list(data)
            if len(flat) != expected:
                raise ValueError("data length does not match tensor shape")
            self._data = [float(value) for value in flat]

        self._strides = self._make_strides(self._shape)

    @classmethod
    def zeros(cls, shape):
        shape = cls._validate_shape_static(shape)
        return cls([0.0] * cls._product_static(shape), shape)

    @classmethod
    def ones(cls, shape):
        shape = cls._validate_shape_static(shape)
        return cls([1.0] * cls._product_static(shape), shape)

    @staticmethod
    def _validate_shape_static(shape):
        values = [int(value) for value in shape]
        for value in values:
            if value < 0:
                raise ValueError("tensor dimensions cannot be negative")
        return values

    def _validate_shape(self, shape):
        return self._validate_shape_static(shape)

    @staticmethod
    def _product_static(values):
        result = 1
        for value in values:
            result *= value
        return result

    def _product(self, values):
        return self._product_static(values)

    @staticmethod
    def _make_strides(shape):
        if len(shape) == 0:
            return []
        strides = [1] * len(shape)
        index = len(shape) - 2
        while index >= 0:
            strides[index] = strides[index + 1] * shape[index + 1]
            index -= 1
        return strides

    def _flatten_and_infer(self, data):
        if not isinstance(data, (list, tuple)):
            return [data], []
        if len(data) == 0:
            return [], [0]

        child_flats = []
        child_shape = None
        for item in data:
            flat, shape = self._flatten_and_infer(item)
            if child_shape is None:
                child_shape = shape
            elif child_shape != shape:
                raise ValueError("ragged nested data cannot form a dense tensor")
            child_flats.extend(flat)
        return child_flats, [len(data)] + child_shape

    @property
    def shape(self):
        return tuple(self._shape)

    @property
    def ndim(self):
        return len(self._shape)

    @property
    def size(self):
        return len(self._data)

    def copy(self):
        return Tensor(self)

    def flatten(self):
        return self._data[:]

    def _flat_index(self, indices):
        if not isinstance(indices, tuple):
            indices = (indices,)
        if len(indices) != self.ndim:
            raise IndexError("number of tensor indices does not match tensor rank")
        flat = 0
        for axis in range(self.ndim):
            index = indices[axis]
            if index < 0:
                index += self._shape[axis]
            if index < 0 or index >= self._shape[axis]:
                raise IndexError("tensor index out of range")
            flat += index * self._strides[axis]
        return flat

    def __getitem__(self, indices):
        return self._data[self._flat_index(indices)]

    def __setitem__(self, indices, value):
        self._data[self._flat_index(indices)] = float(value)

    def reshape(self, shape):
        shape = self._validate_shape(shape)
        if self._product(shape) != self.size:
            raise ValueError("reshape must preserve the number of elements")
        return Tensor(self._data, shape)

    def _validate_other(self, other):
        if not isinstance(other, Tensor):
            other = Tensor(other)
        if self.shape != other.shape:
            raise ValueError("tensor shapes must match")
        return other

    def add(self, other):
        if isinstance(other, (int, float)):
            return Tensor([value + other for value in self._data], self._shape)
        other = self._validate_other(other)
        return Tensor([self._data[i] + other._data[i] for i in range(self.size)], self._shape)

    def subtract(self, other):
        if isinstance(other, (int, float)):
            return Tensor([value - other for value in self._data], self._shape)
        other = self._validate_other(other)
        return Tensor([self._data[i] - other._data[i] for i in range(self.size)], self._shape)

    def multiply(self, other):
        if isinstance(other, (int, float)):
            return Tensor([value * other for value in self._data], self._shape)
        other = self._validate_other(other)
        return Tensor([self._data[i] * other._data[i] for i in range(self.size)], self._shape)

    def divide(self, other):
        if isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("division by zero")
            return Tensor([value / other for value in self._data], self._shape)
        other = self._validate_other(other)
        result = []
        for i in range(self.size):
            if other._data[i] == 0:
                raise ZeroDivisionError("division by zero")
            result.append(self._data[i] / other._data[i])
        return Tensor(result, self._shape)

    def sum(self):
        total = 0.0
        for value in self._data:
            total += value
        return total

    def mean(self):
        if self.size == 0:
            raise ValueError("mean of empty tensor")
        return self.sum() / self.size

    def map(self, function):
        return Tensor([function(value) for value in self._data], self._shape)

    def transpose2d(self):
        if self.ndim != 2:
            raise ValueError("transpose2d requires a rank-2 tensor")
        rows, cols = self._shape
        values = []
        for j in range(cols):
            for i in range(rows):
                values.append(self[i, j])
        return Tensor(values, [cols, rows])

    def matmul(self, other):
        if not isinstance(other, Tensor):
            other = Tensor(other)
        if self.ndim != 2 or other.ndim != 2:
            raise ValueError("matmul currently supports rank-2 tensors")
        left_rows, left_cols = self._shape
        right_rows, right_cols = other._shape
        if left_cols != right_rows:
            raise ValueError("inner tensor dimensions must match")
        result = Tensor.zeros([left_rows, right_cols])
        for i in range(left_rows):
            for k in range(left_cols):
                left = self[i, k]
                for j in range(right_cols):
                    result[i, j] = result[i, j] + (left * other[k, j])
        return result

    def to_nested(self):
        if self.ndim == 0:
            return self._data[0] if self._data else None

        def build(axis, offset):
            if axis == self.ndim - 1:
                length = self._shape[axis]
                return self._data[offset:offset + length]
            result = []
            step = self._strides[axis]
            for i in range(self._shape[axis]):
                result.append(build(axis + 1, offset + i * step))
            return result

        return build(0, 0)

    def __repr__(self):
        return "Tensor(shape=" + repr(self.shape) + ", data=" + repr(self.to_nested()) + ")"
