
class Queue:
    def __init__(self, initial_capacity=8):
        if initial_capacity < 1:
            raise ValueError("initial_capacity must be >= 1")
        self._capacity = initial_capacity
        self._data = [None] * initial_capacity
        self._head = 0
        self._tail = 0
        self._size = 0

    def __len__(self):
        return self._size

    def is_empty(self):
        return self._size == 0

    def _resize(self, new_capacity):
        new_data = [None] * new_capacity
        i = 0
        while i < self._size:
            new_data[i] = self._data[(self._head + i) % self._capacity]
            i += 1
        self._data = new_data
        self._capacity = new_capacity
        self._head = 0
        self._tail = self._size

    def enqueue(self, value):
        if self._size == self._capacity:
            self._resize(self._capacity * 2)
        self._data[self._tail] = value
        self._tail = (self._tail + 1) % self._capacity
        self._size += 1

    def dequeue(self):
        if self._size == 0:
            raise IndexError("dequeue from empty Queue")
        value = self._data[self._head]
        self._data[self._head] = None
        self._head = (self._head + 1) % self._capacity
        self._size -= 1
        return value

    def peek(self):
        if self._size == 0:
            raise IndexError("peek from empty Queue")
        return self._data[self._head]

    def clear(self):
        self._capacity = 8
        self._data = [None] * self._capacity
        self._head = 0
        self._tail = 0
        self._size = 0

    def to_list(self):
        result = [None] * self._size
        i = 0
        while i < self._size:
            result[i] = self._data[(self._head + i) % self._capacity]
            i += 1
        return result
