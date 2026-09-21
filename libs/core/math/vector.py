"""One-dimensional numerical vector primitives with no imports."""


class Vector:
    def __init__(self, values):
        if isinstance(values, Vector):
            self._data = values.to_list()
        else:
            self._data = [float(value) for value in values]

    @classmethod
    def zeros(cls, size):
        if size < 0:
            raise ValueError("size cannot be negative")
        return cls([0.0] * size)

    @classmethod
    def ones(cls, size):
        if size < 0:
            raise ValueError("size cannot be negative")
        return cls([1.0] * size)

    def copy(self):
        return Vector(self._data)

    def to_list(self):
        return self._data[:]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        index = 0
        while index < len(self._data):
            yield self._data[index]
            index += 1

    def __getitem__(self, index):
        return self._data[index]

    def __setitem__(self, index, value):
        self._data[index] = float(value)

    def _validate_other(self, other):
        if not isinstance(other, Vector):
            other = Vector(other)
        if len(self) != len(other):
            raise ValueError("vector sizes must match")
        return other

    def add(self, other):
        other = self._validate_other(other)
        return Vector([self._data[i] + other[i] for i in range(len(self))])

    def subtract(self, other):
        other = self._validate_other(other)
        return Vector([self._data[i] - other[i] for i in range(len(self))])

    def multiply(self, other):
        if isinstance(other, (int, float)):
            return self.scale(other)
        other = self._validate_other(other)
        return Vector([self._data[i] * other[i] for i in range(len(self))])

    def divide(self, other):
        if isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("division by zero")
            return Vector([value / other for value in self._data])
        other = self._validate_other(other)
        result = []
        for i in range(len(self)):
            if other[i] == 0:
                raise ZeroDivisionError("division by zero")
            result.append(self._data[i] / other[i])
        return Vector(result)

    def scale(self, scalar):
        return Vector([value * scalar for value in self._data])

    def dot(self, other):
        other = self._validate_other(other)
        total = 0.0
        for i in range(len(self)):
            total += self._data[i] * other[i]
        return total

    def sum(self):
        total = 0.0
        for value in self._data:
            total += value
        return total

    def mean(self):
        if len(self) == 0:
            raise ValueError("mean of empty vector")
        return self.sum() / len(self)

    def squared_norm(self):
        return self.dot(self)

    def norm(self):
        value = self.squared_norm()
        if 'sqrt' in globals():
            return sqrt(value)
        if value == 0:
            return 0.0
        guess = value if value >= 1 else 1.0
        for _ in range(80):
            guess = 0.5 * (guess + value / guess)
        return guess

    def normalized(self, epsilon=1e-12):
        magnitude = self.norm()
        if magnitude <= epsilon:
            raise ValueError("cannot normalize a near-zero vector")
        return self.divide(magnitude)

    def map(self, function):
        return Vector([function(value) for value in self._data])

    def max(self):
        if len(self) == 0:
            raise ValueError("max of empty vector")
        best = self._data[0]
        for value in self._data[1:]:
            if value > best:
                best = value
        return best

    def min(self):
        if len(self) == 0:
            raise ValueError("min of empty vector")
        best = self._data[0]
        for value in self._data[1:]:
            if value < best:
                best = value
        return best

    def argmax(self):
        if len(self) == 0:
            raise ValueError("argmax of empty vector")
        best_index = 0
        best_value = self._data[0]
        for i in range(1, len(self._data)):
            if self._data[i] > best_value:
                best_value = self._data[i]
                best_index = i
        return best_index

    def __repr__(self):
        return "Vector(" + repr(self._data) + ")"
