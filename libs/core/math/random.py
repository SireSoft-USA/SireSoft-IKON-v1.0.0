"""Deterministic pseudo-random number generation without imports.

Uses xorshift64* as a compact reproducible generator. It is suitable for model
initialization/testing, not for cryptography.
"""


class RandomGenerator:
    _MASK = (1 << 64) - 1
    _MULTIPLIER = 2685821657736338717

    def __init__(self, seed=88172645463325252):
        self.seed(seed)

    def seed(self, value):
        state = int(value) & self._MASK
        if state == 0:
            state = 0x9E3779B97F4A7C15
        self._state = state
        return self

    def _next_uint64(self):
        x = self._state
        x ^= (x >> 12)
        x ^= (x << 25) & self._MASK
        x ^= (x >> 27)
        self._state = x & self._MASK
        return (self._state * self._MULTIPLIER) & self._MASK

    def random(self):
        # Keep 53 bits so conversion to IEEE-754 double is deterministic.
        value = self._next_uint64() >> 11
        return value / float(1 << 53)

    def uniform(self, low=0.0, high=1.0):
        if high < low:
            raise ValueError("high must be greater than or equal to low")
        return low + ((high - low) * self.random())

    def randint(self, low, high):
        if high < low:
            raise ValueError("high must be greater than or equal to low")
        span = (high - low) + 1
        return low + int(self.random() * span)

    def choice(self, values):
        if len(values) == 0:
            raise ValueError("cannot choose from an empty sequence")
        return values[self.randint(0, len(values) - 1)]

    def shuffle(self, values):
        index = len(values) - 1
        while index > 0:
            swap_index = self.randint(0, index)
            values[index], values[swap_index] = values[swap_index], values[index]
            index -= 1
        return values


_GLOBAL_RANDOM = RandomGenerator(1337)


def set_seed(seed):
    _GLOBAL_RANDOM.seed(seed)


def random_value():
    return _GLOBAL_RANDOM.random()


def uniform(low=0.0, high=1.0):
    return _GLOBAL_RANDOM.uniform(low, high)


def randint(low, high):
    return _GLOBAL_RANDOM.randint(low, high)
