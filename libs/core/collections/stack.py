
class _StackNode:
    def __init__(self, value, next_node=None):
        self.value = value
        self.next = next_node


class Stack:
    def __init__(self):
        self._top = None
        self._size = 0

    def __len__(self):
        return self._size

    def is_empty(self):
        return self._size == 0

    def push(self, value):
        self._top = _StackNode(value, self._top)
        self._size += 1

    def pop(self):
        if self._top is None:
            raise IndexError("pop from empty Stack")
        value = self._top.value
        self._top = self._top.next
        self._size -= 1
        return value

    def peek(self):
        if self._top is None:
            raise IndexError("peek from empty Stack")
        return self._top.value

    def clear(self):
        self._top = None
        self._size = 0

    def to_list(self):
        result = [None] * self._size
        node = self._top
        i = 0
        while node is not None:
            result[i] = node.value
            i += 1
            node = node.next
        return result
