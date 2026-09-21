"""Computation-graph inspection and traversal utilities.

No imports are used.  Traversal is iterative so deep graphs do not depend on
Python recursion depth.
"""


def topological_sort(root):
    """Return graph nodes in parents-before-child topological order."""
    if not isinstance(root, Value):
        raise TypeError("topological_sort expects a Value root")

    order = []
    visited = {}
    stack = [(root, False)]

    while len(stack) > 0:
        node, expanded = stack.pop()
        node_id = id(node)
        if expanded:
            if node_id not in visited:
                visited[node_id] = True
                order.append(node)
            continue
        if node_id in visited:
            continue

        stack.append((node, True))
        index = len(node._prev) - 1
        while index >= 0:
            parent = node._prev[index]
            if id(parent) not in visited:
                stack.append((parent, False))
            index -= 1

    return order


def graph_nodes(root):
    return topological_sort(root)


def leaf_nodes(root):
    nodes = topological_sort(root)
    leaves = []
    for node in nodes:
        if len(node._prev) == 0:
            leaves.append(node)
    return leaves


def trainable_leaves(root):
    leaves = leaf_nodes(root)
    result = []
    for node in leaves:
        if node.requires_grad:
            result.append(node)
    return result


def zero_graph_gradients(root):
    nodes = topological_sort(root)
    for node in nodes:
        node.zero_grad()
    return len(nodes)


def graph_summary(root):
    nodes = topological_sort(root)
    leaves = 0
    trainable = 0
    operations = {}
    for node in nodes:
        if len(node._prev) == 0:
            leaves += 1
        if node.requires_grad:
            trainable += 1
        name = node._op
        operations[name] = operations.get(name, 0) + 1
    return {
        "nodes": len(nodes),
        "leaves": leaves,
        "trainable_nodes": trainable,
        "operations": operations,
    }
