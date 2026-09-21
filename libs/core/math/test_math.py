"""Self-contained test runner for every file in libs/core/math.

Run from the SireLLM project root:
    python libs/core/math/test_math.py

No testing framework or import statement is used.
"""

BASE = "libs/core/math/"
FILES = [
    "scalar.py",
    "random.py",
    "vector.py",
    "matrix.py",
    "tensor.py",
    "linalg.py",
    "statistics.py",
]

namespace = {"__builtins__": __builtins__}
for filename in FILES:
    path = BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)

globals().update(namespace)

passed = 0


def check(condition, message):
    global passed
    if not condition:
        raise AssertionError(message)
    passed += 1


def close(a, b, tolerance=1e-8):
    return scalar_abs(a - b) <= tolerance


# scalar.py
check(scalar_abs(-5) == 5, "scalar_abs")
check(clamp(12, 0, 10) == 10, "clamp upper")
check(sign(-3) == -1 and sign(0) == 0 and sign(2) == 1, "sign")
check(close(sqrt(81), 9), "sqrt")
check(close(exp(1), E, 1e-8), "exp")
check(close(log(E), 1.0, 1e-8), "log")
check(close(power(9, 0.5), 3.0, 1e-7), "power")
check(close(sigmoid(0), 0.5), "sigmoid")
check(close(tanh(0), 0.0), "tanh")

# random.py
r1 = RandomGenerator(12345)
r2 = RandomGenerator(12345)
seq1 = [r1.random() for _ in range(8)]
seq2 = [r2.random() for _ in range(8)]
check(seq1 == seq2, "random reproducibility")
check(all(0.0 <= value < 1.0 for value in seq1), "random range")
check(10 <= r1.randint(10, 20) <= 20, "randint")
items = [1, 2, 3, 4, 5]
r1.shuffle(items)
check(sorted(items) == [1, 2, 3, 4, 5], "shuffle")

# vector.py
v1 = Vector([1, 2, 3])
v2 = Vector([4, 5, 6])
check(v1.add(v2).to_list() == [5.0, 7.0, 9.0], "vector add")
check(v2.subtract(v1).to_list() == [3.0, 3.0, 3.0], "vector subtract")
check(v1.scale(2).to_list() == [2.0, 4.0, 6.0], "vector scale")
check(v1.dot(v2) == 32.0, "vector dot")
check(close(Vector([3, 4]).norm(), 5.0), "vector norm")
check(Vector([1, 9, 4]).argmax() == 1, "vector argmax")

# matrix.py
m1 = Matrix([[1, 2], [3, 4]])
m2 = Matrix([[5, 6], [7, 8]])
check(m1.add(m2).to_list() == [[6.0, 8.0], [10.0, 12.0]], "matrix add")
check(m1.transpose().to_list() == [[1.0, 3.0], [2.0, 4.0]], "matrix transpose")
check(m1.matmul(m2).to_list() == [[19.0, 22.0], [43.0, 50.0]], "matrix matmul")
check(Matrix.identity(3).to_list() == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], "identity")
check(m1.matvec(Vector([1, 2])).to_list() == [5.0, 11.0], "matrix-vector multiply")

# tensor.py
t = Tensor([[1, 2, 3], [4, 5, 6]])
check(t.shape == (2, 3), "tensor shape")
check(t.ndim == 2 and t.size == 6, "tensor metadata")
check(t[1, 2] == 6.0, "tensor indexing")
t[0, 1] = 9
check(t[0, 1] == 9.0, "tensor assignment")
check(t.reshape([3, 2]).shape == (3, 2), "tensor reshape")
check(Tensor([[1, 2], [3, 4]]).transpose2d().to_nested() == [[1.0, 3.0], [2.0, 4.0]], "tensor transpose")
check(Tensor([[1, 2], [3, 4]]).matmul(Tensor([[5, 6], [7, 8]])).to_nested() == [[19.0, 22.0], [43.0, 50.0]], "tensor matmul")
check(Tensor.ones([2, 2]).add(2).to_nested() == [[3.0, 3.0], [3.0, 3.0]], "tensor scalar add")

# linalg.py
la = Matrix([[4, 7], [2, 6]])
check(close(determinant(la), 10.0), "determinant")
inv = inverse(la)
check(close(inv[0, 0], 0.6) and close(inv[0, 1], -0.7), "inverse row 1")
check(close(inv[1, 0], -0.2) and close(inv[1, 1], 0.4), "inverse row 2")
solution = solve(Matrix([[2, 1], [5, 7]]), Vector([11, 13]))
check(close(solution[0], 64.0 / 9.0) and close(solution[1], -29.0 / 9.0), "linear solve")
check(matmul(Matrix([[1, 2]]), Matrix([[3], [4]])).to_list() == [[11.0]], "linalg matmul")
check(close(vector_norm([6, 8]), 10.0), "linalg norm")

# statistics.py
values = [1, 2, 3, 4, 5]
check(close(mean(values), 3.0), "mean")
check(close(variance(values), 2.0), "population variance")
check(close(variance(values, True), 2.5), "sample variance")
check(close(standard_deviation([3, 3, 3]), 0.0), "std")
check(close(median([5, 1, 4, 2, 3]), 3.0), "median odd")
check(close(median([1, 2, 3, 4]), 2.5), "median even")
check(close(percentile([0, 10, 20, 30], 50), 15.0), "percentile")
check(close(covariance([1, 2, 3], [2, 4, 6]), 4.0 / 3.0), "covariance")

# Integration sanity: Matrix and Tensor agree on matmul.
left = [[1, 2, 3], [4, 5, 6]]
right = [[7, 8], [9, 10], [11, 12]]
matrix_result = Matrix(left).matmul(Matrix(right)).to_list()
tensor_result = Tensor(left).matmul(Tensor(right)).to_nested()
check(matrix_result == tensor_result, "matrix/tensor matmul agreement")

print("MATH TEST SUITE: PASS")
print("Assertions passed:", passed)
print("Files validated:", str(len(FILES)) + "/" + str(len(FILES)))
