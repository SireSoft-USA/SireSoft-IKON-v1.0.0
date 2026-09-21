# Zero-dependency folder test runner.
# It loads only our own handwritten source files using Python built-ins.

BASE = __file__.replace("\\", "/").rsplit("/", 1)[0]


def load_local(filename):
    path = BASE + "/" + filename
    handle = open(path, "r", encoding="utf-8")
    source = handle.read()
    handle.close()
    exec(compile(source, path, "exec"), globals())


load_local("dynamic_array.py")
load_local("linked_list.py")
load_local("hash_map.py")
load_local("hash_set.py")
load_local("stack.py")
load_local("queue.py")
load_local("heap.py")


TESTS_RUN = 0


def check(condition, message):
    global TESTS_RUN
    TESTS_RUN += 1
    if not condition:
        raise AssertionError(message)


def expect_error(error_type, function, message):
    global TESTS_RUN
    TESTS_RUN += 1
    try:
        function()
    except error_type:
        return
    raise AssertionError(message)


def test_dynamic_array():
    a = DynamicArray(2)
    a.append(10)
    a.append(20)
    a.append(30)
    check(a.to_list() == [10, 20, 30], "DynamicArray append/resize failed")
    check(a.capacity >= 3, "DynamicArray capacity failed")
    a.insert(1, 15)
    check(a.to_list() == [10, 15, 20, 30], "DynamicArray insert failed")
    check(a[-1] == 30, "DynamicArray negative indexing failed")
    a[2] = 99
    check(a[2] == 99, "DynamicArray setitem failed")
    check(a.pop(1) == 15, "DynamicArray pop failed")
    check(a.remove(99) == 99, "DynamicArray remove failed")
    check(a.contains(30), "DynamicArray contains failed")
    expect_error(IndexError, lambda: DynamicArray().pop(), "DynamicArray empty pop should fail")


def test_linked_list():
    l = LinkedList()
    l.append(2)
    l.prepend(1)
    l.append(4)
    l.insert(2, 3)
    check(l.to_list() == [1, 2, 3, 4], "LinkedList insert order failed")
    check(l.get(-1) == 4, "LinkedList negative index failed")
    l.set(1, 20)
    check(l.to_list() == [1, 20, 3, 4], "LinkedList set failed")
    check(l.remove(3), "LinkedList remove failed")
    check(l.pop_first() == 1, "LinkedList pop_first failed")
    check(l.pop_last() == 4, "LinkedList pop_last failed")
    check(l.to_list() == [20], "LinkedList final state failed")


def test_hash_map():
    m = HashMap(4)
    i = 0
    while i < 200:
        m.set("key-" + str(i), i * 2)
        i += 1
    check(len(m) == 200, "HashMap size/resize failed")
    check(m.require("key-137") == 274, "HashMap retrieval failed")
    m.set("key-137", 999)
    check(m.require("key-137") == 999, "HashMap update failed")
    check(m.contains_key("key-15"), "HashMap contains_key failed")
    check(m.delete("key-15") == 30, "HashMap delete failed")
    check(not m.contains_key("key-15"), "HashMap delete state failed")
    check(m.get("missing", "fallback") == "fallback", "HashMap default failed")
    expect_error(KeyError, lambda: m.require("missing"), "HashMap require should fail for missing key")


def test_hash_set():
    s = HashSet(4)
    i = 0
    while i < 100:
        s.add("v-" + str(i))
        i += 1
    check(len(s) == 100, "HashSet size/resize failed")
    check(not s.add("v-20"), "HashSet duplicate insert failed")
    check(s.contains("v-77"), "HashSet contains failed")
    check(s.remove("v-77"), "HashSet remove failed")
    check(not s.contains("v-77"), "HashSet remove state failed")
    check(not s.remove("missing"), "HashSet missing remove should be False")


def test_stack():
    s = Stack()
    s.push("a")
    s.push("b")
    s.push("c")
    check(s.peek() == "c", "Stack peek failed")
    check(s.pop() == "c", "Stack LIFO failed")
    check(s.pop() == "b", "Stack LIFO second pop failed")
    check(len(s) == 1, "Stack size failed")
    expect_error(IndexError, lambda: Stack().pop(), "Stack empty pop should fail")


def test_queue():
    q = Queue(2)
    q.enqueue(1)
    q.enqueue(2)
    q.enqueue(3)
    check(q.dequeue() == 1, "Queue FIFO failed")
    q.enqueue(4)
    q.enqueue(5)
    check(q.to_list() == [2, 3, 4, 5], "Queue wrap/resize failed")
    check(q.peek() == 2, "Queue peek failed")
    check(q.dequeue() == 2, "Queue second dequeue failed")
    expect_error(IndexError, lambda: Queue().dequeue(), "Queue empty dequeue should fail")


def test_heap():
    h = MinHeap(2)
    values = [9, 4, 7, 1, 3, 8, 2, 5, 6]
    i = 0
    while i < len(values):
        h.push(values[i])
        i += 1
    check(h.peek() == 1, "MinHeap peek failed")
    check(h.to_sorted_list() == [1, 2, 3, 4, 5, 6, 7, 8, 9], "MinHeap ordering failed")
    check(h.pop() == 1, "MinHeap pop failed")
    check(h.replace_root(10) == 2, "MinHeap replace_root old root failed")
    check(h.peek() == 3, "MinHeap replace_root heapify failed")

    pairs = MinHeap(key_function=lambda item: item[1])
    pairs.push(("b", 5))
    pairs.push(("a", 1))
    pairs.push(("c", 3))
    check(pairs.pop() == ("a", 1), "MinHeap key_function failed")


def run_all():
    test_dynamic_array()
    test_linked_list()
    test_hash_map()
    test_hash_set()
    test_stack()
    test_queue()
    test_heap()
    print("COLLECTIONS TEST SUITE: PASS")
    print("Assertions passed:", TESTS_RUN)
    print("Files validated: 7/7")


if __name__ == "__main__":
    run_all()
