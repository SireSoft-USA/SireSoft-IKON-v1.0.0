
class _LinkedListNode:
    def __init__(self, value, next_node=None, prev_node=None):
        self.value = value
        self.next = next_node
        self.prev = prev_node


class LinkedList:
    def __init__(self):
        self._head = None
        self._tail = None
        self._size = 0

    def __len__(self):
        return self._size

    def is_empty(self):
        return self._size == 0

    def append(self, value):
        node = _LinkedListNode(value, None, self._tail)
        if self._tail is None:
            self._head = node
        else:
            self._tail.next = node
        self._tail = node
        self._size += 1

    def prepend(self, value):
        node = _LinkedListNode(value, self._head, None)
        if self._head is None:
            self._tail = node
        else:
            self._head.prev = node
        self._head = node
        self._size += 1

    def _node_at(self, index):
        if index < 0:
            index += self._size
        if index < 0 or index >= self._size:
            raise IndexError("index out of range")
        if index <= self._size // 2:
            node = self._head
            i = 0
            while i < index:
                node = node.next
                i += 1
            return node
        node = self._tail
        i = self._size - 1
        while i > index:
            node = node.prev
            i -= 1
        return node

    def get(self, index):
        return self._node_at(index).value

    def set(self, index, value):
        self._node_at(index).value = value

    def insert(self, index, value):
        if index < 0:
            index += self._size
            if index < 0:
                index = 0
        if index <= 0:
            self.prepend(value)
            return
        if index >= self._size:
            self.append(value)
            return
        current = self._node_at(index)
        node = _LinkedListNode(value, current, current.prev)
        current.prev.next = node
        current.prev = node
        self._size += 1

    def pop_first(self):
        if self._head is None:
            raise IndexError("pop from empty LinkedList")
        value = self._head.value
        self._head = self._head.next
        self._size -= 1
        if self._head is None:
            self._tail = None
        else:
            self._head.prev = None
        return value

    def pop_last(self):
        if self._tail is None:
            raise IndexError("pop from empty LinkedList")
        value = self._tail.value
        self._tail = self._tail.prev
        self._size -= 1
        if self._tail is None:
            self._head = None
        else:
            self._tail.next = None
        return value

    def remove_at(self, index):
        node = self._node_at(index)
        if node is self._head:
            return self.pop_first()
        if node is self._tail:
            return self.pop_last()
        node.prev.next = node.next
        node.next.prev = node.prev
        self._size -= 1
        return node.value

    def remove(self, value):
        node = self._head
        index = 0
        while node is not None:
            if node.value == value:
                self.remove_at(index)
                return True
            node = node.next
            index += 1
        return False

    def contains(self, value):
        node = self._head
        while node is not None:
            if node.value == value:
                return True
            node = node.next
        return False

    def clear(self):
        self._head = None
        self._tail = None
        self._size = 0

    def to_list(self):
        result = [None] * self._size
        node = self._head
        i = 0
        while node is not None:
            result[i] = node.value
            node = node.next
            i += 1
        return result
