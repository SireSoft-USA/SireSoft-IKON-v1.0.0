
class DynamicArray:
    def __init__(self, initial_capacity=8):
        if initial_capacity < 1:
            raise ValueError("initial_capacity must be >= 1")
        self._capacity = initial_capacity
        self._size = 0
        self._data = [None] * initial_capacity

    def __len__(self):
        return self._size

    @property
    def capacity(self):
        return self._capacity

    def _normalize_index(self, index, allow_end=False):
        if index < 0:
            index += self._size
        upper = self._size if allow_end else self._size - 1
        if index < 0 or index > upper:
            raise IndexError("index out of range")
        return index

    def _resize(self, new_capacity):
        if new_capacity < self._size:
            new_capacity = self._size
        if new_capacity < 1:
            new_capacity = 1
        new_data = [None] * new_capacity
        i = 0
        while i < self._size:
            new_data[i] = self._data[i]
            i += 1
        self._data = new_data
        self._capacity = new_capacity

    def append(self, value):
        if self._size == self._capacity:
            self._resize(self._capacity * 2)
        self._data[self._size] = value
        self._size += 1

    def insert(self, index, value):
        if index < 0:
            index += self._size
            if index < 0:
                index = 0
        if index > self._size:
            index = self._size
        if self._size == self._capacity:
            self._resize(self._capacity * 2)
        i = self._size
        while i > index:
            self._data[i] = self._data[i - 1]
            i -= 1
        self._data[index] = value
        self._size += 1

    def pop(self, index=-1):
        if self._size == 0:
            raise IndexError("pop from empty DynamicArray")
        index = self._normalize_index(index)
        value = self._data[index]
        i = index
        while i < self._size - 1:
            self._data[i] = self._data[i + 1]
            i += 1
        self._size -= 1
        self._data[self._size] = None
        if self._capacity > 8 and self._size <= self._capacity // 4:
            target = self._capacity // 2
            if target < 8:
                target = 8
            self._resize(target)
        return value

    def remove(self, value):
        index = self.index_of(value)
        if index == -1:
            raise ValueError("value not found")
        return self.pop(index)

    def index_of(self, value):
        i = 0
        while i < self._size:
            if self._data[i] == value:
                return i
            i += 1
        return -1

    def contains(self, value):
        return self.index_of(value) != -1

    def clear(self):
        self._capacity = 8
        self._size = 0
        self._data = [None] * self._capacity

    def to_list(self):
        result = [None] * self._size
        i = 0
        while i < self._size:
            result[i] = self._data[i]
            i += 1
        return result

    def __getitem__(self, index):
        return self._data[self._normalize_index(index)]

    def __setitem__(self, index, value):
        self._data[self._normalize_index(index)] = value
