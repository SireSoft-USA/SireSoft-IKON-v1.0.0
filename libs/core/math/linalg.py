"""Linear-algebra algorithms implemented directly on lists/Matrix/Vector."""


def _as_rows(value):
    if hasattr(value, 'to_list'):
        rows = value.to_list()
    else:
        rows = [list(row) for row in value]
    return rows


def dot(a, b):
    left = a.to_list() if hasattr(a, 'to_list') else list(a)
    right = b.to_list() if hasattr(b, 'to_list') else list(b)
    if len(left) != len(right):
        raise ValueError("vector sizes must match")
    total = 0.0
    for i in range(len(left)):
        total += left[i] * right[i]
    return total


def vector_norm(values):
    squared = dot(values, values)
    if 'sqrt' in globals():
        return sqrt(squared)
    if squared == 0:
        return 0.0
    guess = squared if squared >= 1 else 1.0
    for _ in range(80):
        guess = 0.5 * (guess + squared / guess)
    return guess


def transpose(matrix):
    rows = _as_rows(matrix)
    if len(rows) == 0:
        return Matrix([]) if 'Matrix' in globals() else []
    width = len(rows[0])
    result = [[rows[i][j] for i in range(len(rows))] for j in range(width)]
    return Matrix(result) if 'Matrix' in globals() else result


def matmul(left, right):
    a = _as_rows(left)
    b = _as_rows(right)
    if len(a) == 0 or len(b) == 0:
        result = []
        return Matrix(result) if 'Matrix' in globals() else result
    if len(a[0]) != len(b):
        raise ValueError("inner matrix dimensions must match")
    rows = len(a)
    inner = len(b)
    cols = len(b[0])
    result = [[0.0 for _ in range(cols)] for _ in range(rows)]
    for i in range(rows):
        for k in range(inner):
            value = a[i][k]
            for j in range(cols):
                result[i][j] += value * b[k][j]
    return Matrix(result) if 'Matrix' in globals() else result


def determinant(matrix):
    rows = _as_rows(matrix)
    n = len(rows)
    if n == 0:
        return 1.0
    for row in rows:
        if len(row) != n:
            raise ValueError("determinant requires a square matrix")

    work = [[float(value) for value in row] for row in rows]
    sign_value = 1.0
    det = 1.0

    for pivot in range(n):
        best = pivot
        best_abs = scalar_abs(work[pivot][pivot]) if 'scalar_abs' in globals() else abs(work[pivot][pivot])
        for row in range(pivot + 1, n):
            current_abs = scalar_abs(work[row][pivot]) if 'scalar_abs' in globals() else abs(work[row][pivot])
            if current_abs > best_abs:
                best = row
                best_abs = current_abs
        if best_abs <= 1e-15:
            return 0.0
        if best != pivot:
            work[pivot], work[best] = work[best], work[pivot]
            sign_value *= -1.0

        pivot_value = work[pivot][pivot]
        det *= pivot_value
        for row in range(pivot + 1, n):
            factor = work[row][pivot] / pivot_value
            work[row][pivot] = 0.0
            for col in range(pivot + 1, n):
                work[row][col] -= factor * work[pivot][col]

    return sign_value * det


def solve(matrix, vector):
    rows = _as_rows(matrix)
    rhs = vector.to_list() if hasattr(vector, 'to_list') else list(vector)
    n = len(rows)
    if n == 0 or len(rhs) != n:
        raise ValueError("system dimensions are invalid")
    for row in rows:
        if len(row) != n:
            raise ValueError("solve requires a square coefficient matrix")

    aug = [[float(value) for value in rows[i]] + [float(rhs[i])] for i in range(n)]

    for pivot in range(n):
        best = pivot
        best_abs = scalar_abs(aug[pivot][pivot]) if 'scalar_abs' in globals() else abs(aug[pivot][pivot])
        for row in range(pivot + 1, n):
            current_abs = scalar_abs(aug[row][pivot]) if 'scalar_abs' in globals() else abs(aug[row][pivot])
            if current_abs > best_abs:
                best = row
                best_abs = current_abs
        if best_abs <= 1e-15:
            raise ValueError("matrix is singular")
        if best != pivot:
            aug[pivot], aug[best] = aug[best], aug[pivot]

        pivot_value = aug[pivot][pivot]
        for col in range(pivot, n + 1):
            aug[pivot][col] /= pivot_value

        for row in range(n):
            if row == pivot:
                continue
            factor = aug[row][pivot]
            if factor == 0:
                continue
            for col in range(pivot, n + 1):
                aug[row][col] -= factor * aug[pivot][col]

    result = [aug[i][n] for i in range(n)]
    return Vector(result) if 'Vector' in globals() else result


def inverse(matrix):
    rows = _as_rows(matrix)
    n = len(rows)
    if n == 0:
        return Matrix([]) if 'Matrix' in globals() else []
    for row in rows:
        if len(row) != n:
            raise ValueError("inverse requires a square matrix")

    aug = []
    for i in range(n):
        row = [float(value) for value in rows[i]]
        row.extend([1.0 if i == j else 0.0 for j in range(n)])
        aug.append(row)

    for pivot in range(n):
        best = pivot
        best_abs = scalar_abs(aug[pivot][pivot]) if 'scalar_abs' in globals() else abs(aug[pivot][pivot])
        for row in range(pivot + 1, n):
            current_abs = scalar_abs(aug[row][pivot]) if 'scalar_abs' in globals() else abs(aug[row][pivot])
            if current_abs > best_abs:
                best = row
                best_abs = current_abs
        if best_abs <= 1e-15:
            raise ValueError("matrix is singular")
        if best != pivot:
            aug[pivot], aug[best] = aug[best], aug[pivot]

        pivot_value = aug[pivot][pivot]
        for col in range(2 * n):
            aug[pivot][col] /= pivot_value

        for row in range(n):
            if row == pivot:
                continue
            factor = aug[row][pivot]
            if factor == 0:
                continue
            for col in range(2 * n):
                aug[row][col] -= factor * aug[pivot][col]

    result = [row[n:] for row in aug]
    return Matrix(result) if 'Matrix' in globals() else result
