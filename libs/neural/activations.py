class ReLU(Layer):
    def __init__(self):
        Layer.__init__(self)

    def forward(self, value):
        return Value.ensure(value).relu()


class Sigmoid(Layer):
    def __init__(self):
        Layer.__init__(self)

    def forward(self, value):
        return Value.ensure(value).sigmoid()


class Tanh(Layer):
    def __init__(self):
        Layer.__init__(self)

    def forward(self, value):
        return Value.ensure(value).tanh()


class GELU(Layer):
    """
    tanh approximation used by many Transformer implementations:

      0.5*x*(1 + tanh(sqrt(2/pi)*(x + 0.044715*x^3)))

    It is built entirely from our Value operations, so autograd works without a
    separate derivative implementation.
    """

    def __init__(self):
        Layer.__init__(self)
        self._coefficient = sqrt(2.0 / PI)
        self._cubic = 0.044715

    def forward(self, value):
        x = Value.ensure(value)
        inner = self._coefficient * (x + self._cubic * (x ** 3))
        return 0.5 * x * (1.0 + inner.tanh())


class SiLU(Layer):
    def __init__(self):
        Layer.__init__(self)

    def forward(self, value):
        x = Value.ensure(value)
        return x * x.sigmoid()
