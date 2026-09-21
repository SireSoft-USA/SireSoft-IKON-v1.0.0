
class _HashNode:
    def __init__(self, key, value, next_node=None):
        self.key = key
        self.value = value
        self.next = next_node


class HashMap:
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

    @property
    def capacity(self):
        return self._capacity

    def _key_bytes(self, key):
        if key is None:
            return b"N"
        if key is True:
            return b"B1"
        if key is False:
            return b"B0"
        if isinstance(key, str):
            return ("S" + key).encode("utf-8")
        if isinstance(key, int):
            return ("I" + str(key)).encode("ascii")
        if isinstance(key, float):
            return ("F" + repr(key)).encode("ascii")
        if isinstance(key, bytes):
            return b"Y" + key
        raise TypeError("HashMap keys must be str, int, float, bool, bytes, or None")

    def _hash(self, key):
        data = self._key_bytes(key)
        h = self._FNV_OFFSET
        i = 0
        while i < len(data):
            h ^= data[i]
            h = (h * self._FNV_PRIME) & self._MASK_64
            i += 1
        return h

    def _bucket_index(self, key):
        return self._hash(key) & (self._capacity - 1)

    def _find_node(self, key):
        node = self._buckets[self._bucket_index(key)]
        while node is not None:
            if node.key == key:
                return node
            node = node.next
        return None

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
                index = self._bucket_index(node.key)
                node.next = self._buckets[index]
                self._buckets[index] = node
                node = next_node
            i += 1

    def set(self, key, value):
        index = self._bucket_index(key)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return False
            node = node.next

        if (self._size + 1) > int(self._capacity * self._load_factor):
            self._resize(self._capacity * 2)
            index = self._bucket_index(key)

        self._buckets[index] = _HashNode(key, value, self._buckets[index])
        self._size += 1
        return True

    def get(self, key, default=None):
        node = self._find_node(key)
        if node is None:
            return default
        return node.value

    def require(self, key):
        node = self._find_node(key)
        if node is None:
            raise KeyError(key)
        return node.value

    def contains_key(self, key):
        return self._find_node(key) is not None

    def delete(self, key):
        index = self._bucket_index(key)
        previous = None
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                if previous is None:
                    self._buckets[index] = node.next
                else:
                    previous.next = node.next
                self._size -= 1
                return node.value
            previous = node
            node = node.next
        raise KeyError(key)

    def clear(self):
        self._capacity = 16
        self._size = 0
        self._buckets = [None] * self._capacity

    def keys(self):
        result = [None] * self._size
        position = 0
        i = 0
        while i < self._capacity:
            node = self._buckets[i]
            while node is not None:
                result[position] = node.key
                position += 1
                node = node.next
            i += 1
        return result

    def values(self):
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

    def items(self):
        result = [None] * self._size
        position = 0
        i = 0
        while i < self._capacity:
            node = self._buckets[i]
            while node is not None:
                result[position] = (node.key, node.value)
                position += 1
                node = node.next
            i += 1
        return result
