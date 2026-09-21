
class _SetNode:
    def __init__(self, value, next_node=None):
        self.value = value
        self.next = next_node


class HashSet:
    _FNV_OFFSET = 1469598103934665603
    _FNV_PRIME = 1099511628211
    _MASK_64 = 18446744073709551615

    def __init__(self, initial_capacity=16, load_factor=0.75):
        if initial_capacity < 4:
            initial_capacity = 4
        capacity = 1
        while capacity < initial_capacity:
            capacity *= 2
        if load_factor <= 0.0 or load_factor >= 1.0:
            raise ValueError("load_factor must be between 0 and 1")
        self._capacity = capacity
        self._size = 0
        self._load_factor = load_factor
        self._buckets = [None] * self._capacity

    def __len__(self):
        return self._size

    def _value_bytes(self, value):
        if value is None:
            return b"N"
        if value is True:
            return b"B1"
        if value is False:
            return b"B0"
        if isinstance(value, str):
            return ("S" + value).encode("utf-8")
        if isinstance(value, int):
            return ("I" + str(value)).encode("ascii")
        if isinstance(value, float):
            return ("F" + repr(value)).encode("ascii")
        if isinstance(value, bytes):
            return b"Y" + value
        raise TypeError("HashSet values must be str, int, float, bool, bytes, or None")

    def _hash(self, value):
        data = self._value_bytes(value)
        h = self._FNV_OFFSET
        i = 0
        while i < len(data):
            h ^= data[i]
            h = (h * self._FNV_PRIME) & self._MASK_64
            i += 1
        return h

    def _bucket_index(self, value):
        return self._hash(value) & (self._capacity - 1)

    def _resize(self, new_capacity):
        old_buckets = self._buckets
        old_capacity = self._capacity
        self._capacity = new_capacity
        self._buckets = [None] * new_capacity

        i = 0
        while i < old_capacity:
            node = old_buckets[i]
            while node is not None:
                next_node = node.next
                index = self._bucket_index(node.value)
                node.next = self._buckets[index]
                self._buckets[index] = node
                node = next_node
            i += 1

    def contains(self, value):
        node = self._buckets[self._bucket_index(value)]
        while node is not None:
            if node.value == value:
                return True
            node = node.next
        return False

    def add(self, value):
        index = self._bucket_index(value)
        node = self._buckets[index]
        while node is not None:
            if node.value == value:
                return False
            node = node.next

        if (self._size + 1) > int(self._capacity * self._load_factor):
            self._resize(self._capacity * 2)
            index = self._bucket_index(value)

        self._buckets[index] = _SetNode(value, self._buckets[index])
        self._size += 1
        return True

    def remove(self, value):
        index = self._bucket_index(value)
        previous = None
        node = self._buckets[index]
        while node is not None:
            if node.value == value:
                if previous is None:
                    self._buckets[index] = node.next
                else:
                    previous.next = node.next
                self._size -= 1
                return True
            previous = node
            node = node.next
        return False

    def clear(self):
        self._capacity = 16
        self._size = 0
        self._buckets = [None] * self._capacity

    def to_list(self):
        result = [None] * self._size
        position = 0
        i = 0
        while i < self._capacity:
            node = self._buckets[i]
            while node is not None:
                result[position] = node.value
                position += 1
                node = node.next
            i += 1
        return result
