"""Dense two-dimensional matrix implementation with no imports."""


class Matrix:
    def __init__(self, rows):
        rows = [list(row) for row in rows]
        if len(rows) == 0:
            self.rows = 0
            self.cols = 0
            self._data = []
            return
        width = len(rows[0])
        for row in rows:
            if len(row) != width:
                raise ValueError("all matrix rows must have the same length")
        self.rows = len(rows)
        self.cols = width
        self._data = [[float(value) for value in row] for row in rows]

    @classmethod
    def zeros(cls, rows, cols):
        if rows < 0 or cols < 0:
            raise ValueError("matrix dimensions cannot be negative")
        return cls([[0.0 for _ in range(cols)] for _ in range(rows)])

    @classmethod
    def ones(cls, rows, cols):
        if rows < 0 or cols < 0:
            raise ValueError("matrix dimensions cannot be negative")
        return cls([[1.0 for _ in range(cols)] for _ in range(rows)])

    @classmethod
    def identity(cls, size):
        if size < 0:
            raise ValueError("size cannot be negative")
        rows = []
        for i in range(size):
            row = []
            for j in range(size):
                row.append(1.0 if i == j else 0.0)
            rows.append(row)
        return cls(rows)

    def shape(self):
        return (self.rows, self.cols)

    def copy(self):
        return Matrix(self.to_list())

    def to_list(self):
        return [row[:] for row in self._data]

    def __getitem__(self, index):
        if isinstance(index, tuple):
            row, col = index
            return self._data[row][col]
        return self._data[index]

    def __setitem__(self, index, value):
        if isinstance(index, tuple):
            row, col = index
            self._data[row][col] = float(value)
            return
        if len(value) != self.cols:
            raise ValueError("replacement row has the wrong width")
        self._data[index] = [float(item) for item in value]

    def _validate_same_shape(self, other):
        if not isinstance(other, Matrix):
            other = Matrix(other)
        if self.shape() != other.shape():
            raise ValueError("matrix shapes must match")
        return other

    def add(self, other):
        other = self._validate_same_shape(other)
        return Matrix([
            [self._data[i][j] + other[i, j] for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def subtract(self, other):
        other = self._validate_same_shape(other)
        return Matrix([
            [self._data[i][j] - other[i, j] for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def hadamard(self, other):
        other = self._validate_same_shape(other)
        return Matrix([
            [self._data[i][j] * other[i, j] for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def scale(self, scalar):
        return Matrix([
            [self._data[i][j] * scalar for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def transpose(self):
        if self.rows == 0:
            return Matrix([])
        return Matrix([
            [self._data[i][j] for i in range(self.rows)]
            for j in range(self.cols)
        ])

    def matmul(self, other):
        if not isinstance(other, Matrix):
            other = Matrix(other)
        if self.cols != other.rows:
            raise ValueError("inner matrix dimensions must match")
        result = Matrix.zeros(self.rows, other.cols)
        for i in range(self.rows):
            for k in range(self.cols):
                left = self._data[i][k]
                for j in range(other.cols):
                    result._data[i][j] += left * other[k, j]
        return result

    def matvec(self, vector):
        values = vector.to_list() if hasattr(vector, 'to_list') else list(vector)
        if len(values) != self.cols:
            raise ValueError("vector length must equal matrix column count")
        result = []
        for i in range(self.rows):
            total = 0.0
            for j in range(self.cols):
                total += self._data[i][j] * values[j]
            result.append(total)
        if 'Vector' in globals():
            return Vector(result)
        return result

    def sum(self):
        total = 0.0
        for row in self._data:
            for value in row:
                total += value
        return total

    def map(self, function):
        return Matrix([
            [function(self._data[i][j]) for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def flatten(self):
        values = []
        for row in self._data:
            values.extend(row)
        return values

    def __repr__(self):
        return "Matrix(" + repr(self._data) + ")"
