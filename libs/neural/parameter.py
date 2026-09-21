class Parameter(Value):
    """
    Trainable Value used by neural-network layers.
    """

    def __init__(self, data, name=""):
        Value.__init__(
            self,
            data,
            requires_grad=True,
            label=name,
            _children=None,
            _op="parameter",
        )
        self.name = str(name)

    def set_data(self, data):
        if isinstance(data, Tensor):
            tensor = data.copy()
        else:
            tensor = Tensor(data)

        if tensor.shape != self.data.shape:
            raise ValueError("new parameter data must keep the same shape")

        self.data = tensor
        return self

    def element_count(self):
        return self.data.size

    def __repr__(self):
        return (
            "Parameter(name=" + repr(self.name)
            + ", shape=" + repr(self.shape)
            + ")"
        )
