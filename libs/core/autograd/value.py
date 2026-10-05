"""Reverse-mode automatic differentiation value for SireLLM.

The implementation operates on the handwritten Tensor type and uses the
handwritten scalar functions (exp/log/tanh) loaded from ``libs/core/math``.
There are no imports and no external numerical libraries.
"""


def _value_gpu_enabled():
    return (
        "GPU_BACKEND" in globals()
        and GPU_BACKEND is not None
        and GPU_BACKEND.enabled()
    )


class Value:
    """A differentiable tensor node in a dynamic computation graph."""

    def __init__(self, data, requires_grad=True, label="", _children=None, _op="leaf"):
        if isinstance(data, Tensor):
            self.data = data.copy()
        elif isinstance(data, (int, float)):
            self.data = _scalar_tensor(data)
        else:
            self.data = Tensor(data)

        self.requires_grad = bool(requires_grad)
        self.grad = _zeros_like(self.data)
        self.label = str(label)
        self._prev = [] if _children is None else [child for child in _children]
        self._op = str(_op)
        self._backward = self._noop_backward

    def _noop_backward(self):
        return None

    @staticmethod
    def ensure(value, requires_grad=False):
        if isinstance(value, Value):
            return value
        return Value(value, requires_grad=requires_grad)

    @property
    def shape(self):
        return self.data.shape

    @property
    def ndim(self):
        return self.data.ndim

    @property
    def size(self):
        return self.data.size

    def item(self):
        if self.data.size != 1:
            raise ValueError("item() requires exactly one tensor element")
        return self.data.flatten()[0]

    def grad_item(self):
        if self.grad.size != 1:
            raise ValueError("grad_item() requires exactly one gradient element")
        return self.grad.flatten()[0]

    def zero_grad(self):
        self.grad = _zeros_like(self.data)
        return self

    def detach(self):
        return Value(self.data, requires_grad=False, label=self.label)

    def _accumulate(self, gradient):
        if not self.requires_grad:
            return
        if gradient.shape != self.data.shape:
            raise ValueError("attempted to accumulate a gradient with the wrong shape")
        self.grad = _add_gradients(self.grad, gradient)

    def add(self, other):
        other = Value.ensure(other)
        result_data = _binary_tensor(self.data, other.data, "add")
        requires = self.requires_grad or other.requires_grad
        out = Value(result_data, requires, _children=[self, other], _op=ADD.name)

        def _backward():
            if self.requires_grad:
                self._accumulate(_sum_to_shape(out.grad, self.data.shape))
            if other.requires_grad:
                other._accumulate(_sum_to_shape(out.grad, other.data.shape))

        out._backward = _backward
        return out

    def subtract(self, other):
        other = Value.ensure(other)
        result_data = _binary_tensor(self.data, other.data, "subtract")
        requires = self.requires_grad or other.requires_grad
        out = Value(result_data, requires, _children=[self, other], _op=SUBTRACT.name)

        def _backward():
            if self.requires_grad:
                self._accumulate(_sum_to_shape(out.grad, self.data.shape))
            if other.requires_grad:
                negative = out.grad.multiply(-1.0)
                other._accumulate(_sum_to_shape(negative, other.data.shape))

        out._backward = _backward
        return out

    def multiply(self, other):
        other = Value.ensure(other)
        result_data = _binary_tensor(self.data, other.data, "multiply")
        requires = self.requires_grad or other.requires_grad
        out = Value(result_data, requires, _children=[self, other], _op=MULTIPLY.name)

        def _backward():
            if self.requires_grad:
                local = _binary_tensor(out.grad, other.data, "multiply")
                self._accumulate(_sum_to_shape(local, self.data.shape))
            if other.requires_grad:
                local = _binary_tensor(out.grad, self.data, "multiply")
                other._accumulate(_sum_to_shape(local, other.data.shape))

        out._backward = _backward
        return out

    def divide(self, other):
        other = Value.ensure(other)
        result_data = _binary_tensor(self.data, other.data, "divide")
        requires = self.requires_grad or other.requires_grad
        out = Value(result_data, requires, _children=[self, other], _op=DIVIDE.name)

        def _backward():
            if self.requires_grad:
                local = _binary_tensor(out.grad, other.data, "divide")
                self._accumulate(_sum_to_shape(local, self.data.shape))
            if other.requires_grad:
                numerator = _binary_tensor(out.grad, self.data, "multiply").multiply(-1.0)
                denominator = _binary_tensor(other.data, other.data, "multiply")
                local = _binary_tensor(numerator, denominator, "divide")
                other._accumulate(_sum_to_shape(local, other.data.shape))

        out._backward = _backward
        return out

    def power(self, exponent):
        if not isinstance(exponent, (int, float)):
            raise TypeError("power currently requires a numeric constant exponent")
        source = self.data.flatten()
        if _value_gpu_enabled() and len(source) > 0:
            output = GPU_BACKEND.power(source, exponent)
        else:
            output = [0.0] * len(source)
            index = 0
            while index < len(source):
                output[index] = power(source[index], exponent)
                index += 1
        out = Value(Tensor(output, [d for d in self.data.shape]), self.requires_grad, _children=[self], _op=POWER.name)

        def _backward():
            if not self.requires_grad:
                return
            upstream = out.grad.flatten()
            if _value_gpu_enabled() and len(source) > 0:
                gradient = GPU_BACKEND.activation_backward(
                    source, output, upstream, "power", exponent
                )
            else:
                gradient = [0.0] * len(source)
                i = 0
                while i < len(source):
                    if exponent == 0:
                        derivative = 0.0
                    else:
                        derivative = exponent * power(source[i], exponent - 1)
                    gradient[i] = upstream[i] * derivative
                    i += 1
            self._accumulate(Tensor(gradient, [d for d in self.data.shape]))

        out._backward = _backward
        return out

    def matmul(self, other):
        other = Value.ensure(other)
        if self.data.ndim != 2 or other.data.ndim != 2:
            raise ValueError("autograd matmul currently supports rank-2 tensors")
        result = self.data.matmul(other.data)
        requires = self.requires_grad or other.requires_grad
        out = Value(result, requires, _children=[self, other], _op=MATMUL.name)

        def _backward():
            if self.requires_grad:
                gradient = out.grad.matmul(other.data.transpose2d())
                self._accumulate(gradient)
            if other.requires_grad:
                gradient = self.data.transpose2d().matmul(out.grad)
                other._accumulate(gradient)

        out._backward = _backward
        return out

    def sum(self):
        out = Value(self.data.sum(), self.requires_grad, _children=[self], _op=SUM.name)

        def _backward():
            if not self.requires_grad:
                return
            scale = out.grad.flatten()[0]
            self._accumulate(_ones_like(self.data).multiply(scale))

        out._backward = _backward
        return out

    def mean(self):
        if self.data.size == 0:
            raise ValueError("mean of empty tensor")
        out = Value(self.data.mean(), self.requires_grad, _children=[self], _op=MEAN.name)

        def _backward():
            if not self.requires_grad:
                return
            scale = out.grad.flatten()[0] / self.data.size
            self._accumulate(_ones_like(self.data).multiply(scale))

        out._backward = _backward
        return out

    def reshape(self, shape):
        out = Value(self.data.reshape(shape), self.requires_grad, _children=[self], _op=RESHAPE.name)
        original_shape = [dimension for dimension in self.data.shape]

        def _backward():
            if self.requires_grad:
                self._accumulate(out.grad.reshape(original_shape))

        out._backward = _backward
        return out

    def transpose2d(self):
        out = Value(self.data.transpose2d(), self.requires_grad, _children=[self], _op=TRANSPOSE.name)

        def _backward():
            if self.requires_grad:
                self._accumulate(out.grad.transpose2d())

        out._backward = _backward
        return out

    def exp(self):
        source = self.data.flatten()
        if _value_gpu_enabled() and len(source) > 0:
            values = GPU_BACKEND.unary(source, "exp")
        else:
            values = [0.0] * len(source)
            index = 0
            while index < len(source):
                values[index] = exp(source[index])
                index += 1
        result = Tensor(values, [d for d in self.data.shape])
        out = Value(result, self.requires_grad, _children=[self], _op=EXP.name)

        def _backward():
            if self.requires_grad:
                upstream = out.grad.flatten()
                if _value_gpu_enabled() and len(source) > 0:
                    gradient = GPU_BACKEND.activation_backward(
                        source, values, upstream, "exp"
                    )
                    self._accumulate(Tensor(gradient, [d for d in self.data.shape]))
                else:
                    self._accumulate(_binary_tensor(out.grad, out.data, "multiply"))

        out._backward = _backward
        return out

    def log(self):
        source = self.data.flatten()
        if _value_gpu_enabled() and len(source) > 0:
            values = GPU_BACKEND.unary(source, "log")
        else:
            values = [0.0] * len(source)
            index = 0
            while index < len(source):
                values[index] = log(source[index])
                index += 1
        out = Value(Tensor(values, [d for d in self.data.shape]), self.requires_grad, _children=[self], _op=LOG.name)

        def _backward():
            if self.requires_grad:
                upstream = out.grad.flatten()
                if _value_gpu_enabled() and len(source) > 0:
                    gradient = GPU_BACKEND.activation_backward(
                        source, values, upstream, "log"
                    )
                    self._accumulate(Tensor(gradient, [d for d in self.data.shape]))
                else:
                    self._accumulate(_binary_tensor(out.grad, self.data, "divide"))

        out._backward = _backward
        return out

    def tanh(self):
        source = self.data.flatten()
        if _value_gpu_enabled() and len(source) > 0:
            values = GPU_BACKEND.unary(source, "tanh")
        else:
            values = [0.0] * len(source)
            index = 0
            while index < len(source):
                values[index] = tanh(source[index])
                index += 1
        out = Value(Tensor(values, [d for d in self.data.shape]), self.requires_grad, _children=[self], _op=TANH.name)

        def _backward():
            if not self.requires_grad:
                return
            upstream = out.grad.flatten()
            if _value_gpu_enabled() and len(source) > 0:
                gradient = GPU_BACKEND.activation_backward(
                    source, values, upstream, "tanh"
                )
            else:
                gradient = [0.0] * len(values)
                i = 0
                while i < len(values):
                    gradient[i] = upstream[i] * (1.0 - values[i] * values[i])
                    i += 1
            self._accumulate(Tensor(gradient, [d for d in self.data.shape]))

        out._backward = _backward
        return out

    def sigmoid(self):
        source = self.data.flatten()
        if _value_gpu_enabled() and len(source) > 0:
            values = GPU_BACKEND.unary(source, "sigmoid")
        else:
            values = [0.0] * len(source)
            index = 0
            while index < len(source):
                values[index] = sigmoid(source[index])
                index += 1
        out = Value(Tensor(values, [d for d in self.data.shape]), self.requires_grad, _children=[self], _op=SIGMOID.name)

        def _backward():
            if not self.requires_grad:
                return
            upstream = out.grad.flatten()
            if _value_gpu_enabled() and len(source) > 0:
                gradient = GPU_BACKEND.activation_backward(
                    source, values, upstream, "sigmoid"
                )
            else:
                gradient = [0.0] * len(values)
                i = 0
                while i < len(values):
                    s = values[i]
                    gradient[i] = upstream[i] * s * (1.0 - s)
                    i += 1
            self._accumulate(Tensor(gradient, [d for d in self.data.shape]))

        out._backward = _backward
        return out

    def relu(self):
        source = self.data.flatten()
        if _value_gpu_enabled() and len(source) > 0:
            values = GPU_BACKEND.unary(source, "relu")
        else:
            values = [0.0] * len(source)
            index = 0
            while index < len(source):
                values[index] = source[index] if source[index] > 0.0 else 0.0
                index += 1
        out = Value(Tensor(values, [d for d in self.data.shape]), self.requires_grad, _children=[self], _op=RELU.name)

        def _backward():
            if not self.requires_grad:
                return
            upstream = out.grad.flatten()
            if _value_gpu_enabled() and len(source) > 0:
                gradient = GPU_BACKEND.activation_backward(
                    source, values, upstream, "relu"
                )
            else:
                gradient = [0.0] * len(source)
                i = 0
                while i < len(source):
                    gradient[i] = upstream[i] if source[i] > 0.0 else 0.0
                    i += 1
            self._accumulate(Tensor(gradient, [d for d in self.data.shape]))

        out._backward = _backward
        return out

    def backward(self, gradient=None, zero_existing=False):
        return backward(self, gradient, zero_existing)

    def __add__(self, other):
        return self.add(other)

    def __radd__(self, other):
        return self.add(other)

    def __sub__(self, other):
        return self.subtract(other)

    def __rsub__(self, other):
        return Value.ensure(other).subtract(self)

    def __mul__(self, other):
        return self.multiply(other)

    def __rmul__(self, other):
        return self.multiply(other)

    def __truediv__(self, other):
        return self.divide(other)

    def __rtruediv__(self, other):
        return Value.ensure(other).divide(self)

    def __pow__(self, exponent):
        return self.power(exponent)

    def __matmul__(self, other):
        return self.matmul(other)

    def __neg__(self):
        return self.multiply(-1.0)

    def __repr__(self):
        return (
            "Value(shape=" + repr(self.shape)
            + ", data=" + repr(self.data.to_nested())
            + ", requires_grad=" + repr(self.requires_grad)
            + ", op=" + repr(self._op)
            + ")"
        )
