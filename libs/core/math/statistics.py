"""Basic statistical operations implemented without imports."""


def _values(sequence):
    if hasattr(sequence, 'flatten'):
        return sequence.flatten()
    if hasattr(sequence, 'to_list'):
        values = sequence.to_list()
        if len(values) > 0 and isinstance(values[0], list):
            flat = []
            for row in values:
                flat.extend(row)
            return flat
        return values
    return list(sequence)


def mean(sequence):
    values = _values(sequence)
    if len(values) == 0:
        raise ValueError("mean requires at least one value")
    total = 0.0
    for value in values:
        total += value
    return total / len(values)


def variance(sequence, sample=False):
    values = _values(sequence)
    count = len(values)
    if count == 0:
        raise ValueError("variance requires at least one value")
    if sample and count < 2:
        raise ValueError("sample variance requires at least two values")
    center = mean(values)
    total = 0.0
    for value in values:
        difference = value - center
        total += difference * difference
    denominator = count - 1 if sample else count
    return total / denominator


def standard_deviation(sequence, sample=False):
    value = variance(sequence, sample)
    if 'sqrt' in globals():
        return sqrt(value)
    if value == 0:
        return 0.0
    guess = value if value >= 1 else 1.0
    for _ in range(80):
        guess = 0.5 * (guess + value / guess)
    return guess


def median(sequence):
    values = _values(sequence)
    if len(values) == 0:
        raise ValueError("median requires at least one value")
    values = sorted(values)
    middle = len(values) // 2
    if len(values) % 2 == 1:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2.0


def percentile(sequence, q):
    values = _values(sequence)
    if len(values) == 0:
        raise ValueError("percentile requires at least one value")
    if q < 0 or q > 100:
        raise ValueError("percentile q must be between 0 and 100")
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    position = (q / 100.0) * (len(values) - 1)
    lower = int(position)
    upper = lower + 1
    if upper >= len(values):
        return values[lower]
    weight = position - lower
    return values[lower] * (1.0 - weight) + values[upper] * weight


def covariance(left, right, sample=False):
    a = _values(left)
    b = _values(right)
    if len(a) != len(b):
        raise ValueError("covariance sequences must have equal length")
    if len(a) == 0:
        raise ValueError("covariance requires at least one pair")
    if sample and len(a) < 2:
        raise ValueError("sample covariance requires at least two pairs")
    mean_a = mean(a)
    mean_b = mean(b)
    total = 0.0
    for i in range(len(a)):
        total += (a[i] - mean_a) * (b[i] - mean_b)
    denominator = len(a) - 1 if sample else len(a)
    return total / denominator
