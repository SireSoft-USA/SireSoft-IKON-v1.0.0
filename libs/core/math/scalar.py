"""Scalar numerical primitives implemented from first principles.

No imports are used in this file. These functions intentionally avoid Python's
``math`` module so higher-level numerical code has a dependency-free base.
"""

PI = 3.14159265358979323846264338327950288419716939937510
E = 2.71828182845904523536028747135266249775724709369995
LN2 = 0.69314718055994530941723212145817656807550013436026


def scalar_abs(value):
    return -value if value < 0 else value


def scalar_min(a, b):
    return a if a <= b else b


def scalar_max(a, b):
    return a if a >= b else b


def clamp(value, minimum, maximum):
    if minimum > maximum:
        raise ValueError("minimum cannot be greater than maximum")
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def sign(value):
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def is_close(a, b, rel_tol=1e-9, abs_tol=1e-12):
    difference = scalar_abs(a - b)
    scale = scalar_max(scalar_abs(a), scalar_abs(b))
    tolerance = scalar_max(abs_tol, rel_tol * scale)
    return difference <= tolerance


def sqrt(value, tolerance=1e-12, max_iterations=100):
    """Newton-Raphson square root."""
    if value < 0:
        raise ValueError("sqrt is undefined for negative values")
    if value == 0:
        return 0.0
    guess = value if value >= 1 else 1.0
    iteration = 0
    while iteration < max_iterations:
        next_guess = 0.5 * (guess + value / guess)
        if scalar_abs(next_guess - guess) <= tolerance * scalar_max(1.0, scalar_abs(next_guess)):
            return next_guess
        guess = next_guess
        iteration += 1
    return guess


def exp(value):
    """Exponential using range reduction plus a Taylor series.

    Accurate enough for the numerical scale used by this educational runtime.
    """
    if value == 0:
        return 1.0
    if value < 0:
        return 1.0 / exp(-value)

    # e^x = 2^k * e^r, where r is kept small for fast convergence.
    k = int(value / LN2)
    r = value - (k * LN2)

    term = 1.0
    total = 1.0
    n = 1
    while n <= 80:
        term *= r / n
        total += term
        if scalar_abs(term) < 1e-16:
            break
        n += 1

    if k >= 0:
        return total * (2.0 ** k)
    return total / (2.0 ** (-k))


def log(value):
    """Natural logarithm using range reduction and the atanh series."""
    if value <= 0:
        raise ValueError("log is defined only for positive values")
    if value == 1:
        return 0.0

    k = 0
    scaled = float(value)
    while scaled >= 2.0:
        scaled *= 0.5
        k += 1
    while scaled < 1.0:
        scaled *= 2.0
        k -= 1

    z = (scaled - 1.0) / (scaled + 1.0)
    z_squared = z * z
    term = z
    total = 0.0
    denominator = 1
    count = 0
    while count < 100:
        total += term / denominator
        term *= z_squared
        denominator += 2
        if scalar_abs(term / denominator) < 1e-16:
            break
        count += 1

    return (2.0 * total) + (k * LN2)


def power(base, exponent):
    """Power supporting integer and positive-base real exponents."""
    if exponent == int(exponent):
        exponent = int(exponent)
        if exponent == 0:
            return 1.0
        if exponent < 0:
            return 1.0 / power(base, -exponent)
        result = 1.0
        factor = base
        current = exponent
        while current > 0:
            if current % 2 == 1:
                result *= factor
            factor *= factor
            current //= 2
        return result
    if base <= 0:
        raise ValueError("non-integer exponents require a positive base")
    return exp(exponent * log(base))


def sigmoid(value):
    # Branching avoids unnecessary overflow for large-magnitude values.
    if value >= 0:
        z = exp(-value)
        return 1.0 / (1.0 + z)
    z = exp(value)
    return z / (1.0 + z)


def tanh(value):
    if value > 20:
        return 1.0
    if value < -20:
        return -1.0
    doubled = exp(2.0 * value)
    return (doubled - 1.0) / (doubled + 1.0)
