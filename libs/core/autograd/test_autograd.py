"""Self-contained validation for libs/core/autograd.

Run from the SireLLM project root:
    python libs/core/autograd/test_autograd.py

The runner intentionally uses no import statement or external test framework.
It loads the already-completed handwritten math foundation first, followed by
all files in this folder.
"""

MATH_BASE = "libs/core/math/"
MATH_FILES = [
    "scalar.py",
    "tensor.py",
]

AUTOGRAD_BASE = "libs/core/autograd/"
AUTOGRAD_FILES = [
    "operation.py",
    "value.py",
    "graph.py",
    "backward.py",
]

namespace = {"__builtins__": __builtins__}

for filename in MATH_FILES:
    path = MATH_BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    exec(compile(source, path, "exec"), namespace)

for filename in AUTOGRAD_FILES:
    path = AUTOGRAD_BASE + filename
    source = open(path, "r", encoding="utf-8").read()
    if "import " in source or "from " + "libs" in source:
        raise AssertionError("implementation contains a forbidden import: " + filename)
    exec(compile(source, path, "exec"), namespace)

globals().update(namespace)

passed = 0


def check(condition, message):
    global passed
    if not condition:
        raise AssertionError(message)
    passed += 1


def close(a, b, tolerance=1e-7):
    return scalar_abs(a - b) <= tolerance


def list_close(left, right, tolerance=1e-7):
    if len(left) != len(right):
        return False
    index = 0
    while index < len(left):
        if not close(left[index], right[index], tolerance):
            return False
        index += 1
    return True


# operation.py metadata and broadcasting helpers
check(ADD.name == "add" and ADD.arity == 2, "operation metadata")
check(_broadcast_shape((2, 3), (3,)) == [2, 3], "broadcast vector over matrix")
check(_broadcast_shape((2, 1, 3), (1, 4, 1)) == [2, 4, 3], "multi-axis broadcasting")

# Basic scalar graph: z = x*y + x => dz/dx = y+1, dz/dy = x
x = Value(2.0, label="x")
y = Value(3.0, label="y")
z = (x * y) + x
nodes_visited = z.backward()
check(close(z.item(), 8.0), "scalar forward")
check(close(x.grad_item(), 4.0), "scalar gradient x")
check(close(y.grad_item(), 2.0), "scalar gradient y")
check(nodes_visited >= 4, "backward visited graph")

# Polynomial derivative: x^3 - 2*x at x=2 => 3*x^2 - 2 = 10
p = Value(2.0)
loss = (p ** 3) - (2.0 * p)
loss.backward()
check(close(loss.item(), 4.0), "power forward")
check(close(p.grad_item(), 10.0), "power gradient")

# Division derivative.
a = Value(6.0)
b = Value(2.0)
q = a / b
q.backward()
check(close(q.item(), 3.0), "division forward")
check(close(a.grad_item(), 0.5), "division gradient numerator")
check(close(b.grad_item(), -1.5), "division gradient denominator")

# Elementwise tensor operations and reduction.
t = Value([[1.0, 2.0], [3.0, 4.0]])
r = (t * t).sum()
r.backward()
check(close(r.item(), 30.0), "tensor reduction forward")
check(list_close(t.grad.flatten(), [2.0, 4.0, 6.0, 8.0]), "tensor square gradient")

# Broadcasting: bias [3] added to a [2,3] matrix must accumulate two rows.
features = Value([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
bias = Value([0.1, 0.2, 0.3])
broadcast_loss = (features + bias).sum()
broadcast_loss.backward()
check(list_close(features.grad.flatten(), [1.0] * 6), "broadcast gradient matrix")
check(list_close(bias.grad.flatten(), [2.0, 2.0, 2.0]), "broadcast gradient bias")

# Scalar broadcasting.
scalar = Value(3.0)
vec = Value([1.0, 2.0, 3.0])
scalar_loss = (vec * scalar).sum()
scalar_loss.backward()
check(list_close(vec.grad.flatten(), [3.0, 3.0, 3.0]), "scalar broadcast vector gradient")
check(close(scalar.grad_item(), 6.0), "scalar broadcast reduced gradient")

# Matrix multiplication gradients.
left = Value([[1.0, 2.0], [3.0, 4.0]])
right = Value([[5.0, 6.0], [7.0, 8.0]])
mat_loss = (left @ right).sum()
mat_loss.backward()
check(close(mat_loss.item(), 134.0), "matmul forward")
check(list_close(left.grad.flatten(), [11.0, 15.0, 11.0, 15.0]), "matmul left gradient")
check(list_close(right.grad.flatten(), [4.0, 4.0, 6.0, 6.0]), "matmul right gradient")

# Mean gradient.
m = Value([2.0, 4.0, 8.0, 10.0])
m.mean().backward()
check(list_close(m.grad.flatten(), [0.25, 0.25, 0.25, 0.25]), "mean gradient")

# Reshape and transpose preserve gradient correspondence.
view_source = Value([[1.0, 2.0], [3.0, 4.0]])
view_loss = view_source.reshape([4, 1]).reshape([2, 2]).transpose2d().sum()
view_loss.backward()
check(list_close(view_source.grad.flatten(), [1.0, 1.0, 1.0, 1.0]), "view gradients")

# Activations.
act = Value(0.0)
act.sigmoid().backward()
check(close(act.grad_item(), 0.25), "sigmoid gradient")

act2 = Value(0.0)
act2.tanh().backward()
check(close(act2.grad_item(), 1.0), "tanh gradient")

act3 = Value([-2.0, 0.0, 3.0])
act3.relu().sum().backward()
check(list_close(act3.grad.flatten(), [0.0, 0.0, 1.0]), "relu gradient")

# exp/log composition derivative log(exp(x)) = x.
el = Value([0.5, 1.5])
el.exp().log().sum().backward()
check(list_close(el.grad.flatten(), [1.0, 1.0], 1e-6), "exp/log chain gradient")

# Explicit gradient for non-scalar output.
ng = Value([2.0, 4.0])
out = ng * ng
out.backward(Tensor([1.0, 0.5]))
check(list_close(ng.grad.flatten(), [4.0, 4.0]), "explicit vector root gradient")

# requires_grad=False blocks propagation.
constant = Value([10.0, 20.0], requires_grad=False)
variable = Value([1.0, 2.0])
(variable * constant).sum().backward()
check(list_close(variable.grad.flatten(), [10.0, 20.0]), "constant contributes local derivative")
check(list_close(constant.grad.flatten(), [0.0, 0.0]), "constant has no gradient")

# Graph utilities.
g1 = Value(2.0, label="g1")
g2 = Value(5.0, label="g2")
g3 = (g1 * g2) + (g1 ** 2)
summary = graph_summary(g3)
check(summary["nodes"] >= 5, "graph summary node count")
check(len(trainable_leaves(g3)) == 2, "trainable leaves")
order = topological_sort(g3)
check(order[-1] is g3, "topological root last")

# Gradient accumulation across backward calls for leaves.
acc = Value(3.0)
(acc * 2.0).backward()
(acc * 4.0).backward()
check(close(acc.grad_item(), 6.0), "leaf gradient accumulation")
acc.zero_grad()
check(close(acc.grad_item(), 0.0), "zero_grad")

# zero_existing gives a fresh pass across the full graph.
fresh = Value(2.0)
fresh_loss = fresh * fresh
fresh_loss.backward()
check(close(fresh.grad_item(), 4.0), "fresh first gradient")
fresh_loss.backward(zero_existing=True)
check(close(fresh.grad_item(), 4.0), "fresh reset gradient")

# detach creates a non-trainable graph boundary.
original = Value(7.0)
detached = original.detach()
check(detached.requires_grad is False, "detach requires_grad")
check(close(detached.item(), 7.0), "detach data")

print("AUTOGRAD TEST SUITE: PASS")
print("Assertions passed:", passed)
print("Files validated:", str(len(AUTOGRAD_FILES)) + "/" + str(len(AUTOGRAD_FILES)))
print("Dependency validated: libs/core/math/{scalar.py,tensor.py}")
