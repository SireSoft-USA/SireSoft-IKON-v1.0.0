
class MinHeap:
    def __init__(self, initial_capacity=8, key_function=None):
        if initial_capacity < 1:
            raise ValueError("initial_capacity must be >= 1")
        self._capacity = initial_capacity
        self._data = [None] * initial_capacity
        self._size = 0
        self._key_function = key_function

    def __len__(self):
        return self._size

    def is_empty(self):
        return self._size == 0

    def _key(self, value):
        if self._key_function is None:
            return value
        return self._key_function(value)

    def _less(self, left, right):
        return self._key(left) < self._key(right)

    def _resize(self, new_capacity):
        new_data = [None] * new_capacity
        i = 0
        while i < self._size:
            new_data[i] = self._data[i]
            i += 1
        self._data = new_data
        self._capacity = new_capacity

    def _swap(self, i, j):
        temp = self._data[i]
        self._data[i] = self._data[j]
        self._data[j] = temp

    def push(self, value):
        if self._size == self._capacity:
            self._resize(self._capacity * 2)

        index = self._size
        self._data[index] = value
        self._size += 1

        while index > 0:
            parent = (index - 1) // 2
            if not self._less(self._data[index], self._data[parent]):
                break
            self._swap(index, parent)
            index = parent

    def peek(self):
        if self._size == 0:
            raise IndexError("peek from empty MinHeap")
        return self._data[0]

    def pop(self):
        if self._size == 0:
            raise IndexError("pop from empty MinHeap")

        root = self._data[0]
        self._size -= 1

        if self._size == 0:
            self._data[0] = None
            return root

        self._data[0] = self._data[self._size]
        self._data[self._size] = None

        index = 0
        while True:
            left = index * 2 + 1
            right = left + 1
            smallest = index

            if left < self._size and self._less(self._data[left], self._data[smallest]):
                smallest = left
            if right < self._size and self._less(self._data[right], self._data[smallest]):
                smallest = right
            if smallest == index:
                break

            self._swap(index, smallest)
            index = smallest

        return root

    def replace_root(self, value):
        if self._size == 0:
            self.push(value)
            return None
        old_root = self._data[0]
        self._data[0] = value

        index = 0
        while True:
            left = index * 2 + 1
            right = left + 1
            smallest = index
            if left < self._size and self._less(self._data[left], self._data[smallest]):
                smallest = left
            if right < self._size and self._less(self._data[right], self._data[smallest]):
                smallest = right
            if smallest == index:
                break
            self._swap(index, smallest)
            index = smallest

        return old_root

    def clear(self):
        self._capacity = 8
        self._data = [None] * self._capacity
        self._size = 0

    def to_sorted_list(self):
        copied = MinHeap(self._capacity, self._key_function)
        i = 0
        while i < self._size:
            copied.push(self._data[i])
            i += 1

        result = [None] * self._size
        i = 0
        while not copied.is_empty():
            result[i] = copied.pop()
            i += 1
        return result
