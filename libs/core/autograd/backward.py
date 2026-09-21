"""Reverse-mode backpropagation engine for SireLLM.

No imports are used.  The engine walks the dynamic graph in reverse
 topological order and executes each node's locally-defined derivative.
"""


def _normalize_root_gradient(root, gradient):
    if gradient is None:
        if root.data.size != 1:
            raise ValueError("non-scalar outputs require an explicit gradient")
        return _ones_like(root.data)

    if isinstance(gradient, Tensor):
        result = gradient.copy()
    elif isinstance(gradient, (int, float)):
        result = _scalar_tensor(gradient)
    else:
        result = Tensor(gradient)

    if result.shape != root.data.shape:
        raise ValueError("root gradient shape must match output shape")
    return result


def backward(root, gradient=None, zero_existing=False):
    """Run reverse-mode autodiff from ``root``.

    Returns the number of graph nodes traversed.  By default leaf gradients
    accumulate across calls, matching common deep-learning framework behavior.
    Set ``zero_existing=True`` for a fresh graph-wide backward pass.
    """
    if not isinstance(root, Value):
        raise TypeError("backward expects a Value root")
    if not root.requires_grad:
        return 0

    nodes = topological_sort(root)

    if zero_existing:
        for node in nodes:
            node.zero_grad()
    else:
        # Intermediate gradients must never retain a previous pass; only leaf
        # gradients intentionally accumulate between backward calls.
        for node in nodes:
            if len(node._prev) > 0:
                node.zero_grad()

    root.grad = _normalize_root_gradient(root, gradient)

    index = len(nodes) - 1
    while index >= 0:
        node = nodes[index]
        node._backward()
        index -= 1

    return len(nodes)
