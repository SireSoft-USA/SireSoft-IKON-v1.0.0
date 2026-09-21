class Layer:
    """
    Base layer with explicit parameter/sublayer registration.

    Registration is deliberate rather than reflective, which keeps the runtime
    predictable and avoids depending on inspection helpers.
    """

    def __init__(self):
        self.training = True
        self._parameters = {}
        self._layers = {}

    def register_parameter(self, name, parameter):
        if not isinstance(name, str) or name == "":
            raise ValueError("parameter name must be non-empty str")
        if not isinstance(parameter, Parameter):
            raise TypeError("parameter must be Parameter")
        if name in self._parameters or name in self._layers:
            raise ValueError("duplicate layer member: " + name)

        self._parameters[name] = parameter
        return parameter

    def register_layer(self, name, layer):
        if not isinstance(name, str) or name == "":
            raise ValueError("layer name must be non-empty str")
        if not isinstance(layer, Layer):
            raise TypeError("layer must inherit Layer")
        if name in self._parameters or name in self._layers:
            raise ValueError("duplicate layer member: " + name)

        self._layers[name] = layer
        return layer

    def parameters(self):
        result = []

        for name in self._parameters:
            result.append(self._parameters[name])

        for name in self._layers:
            child_parameters = self._layers[name].parameters()
            for parameter in child_parameters:
                result.append(parameter)

        return result

    def named_parameters(self, prefix=""):
        result = []

        for name in self._parameters:
            full_name = prefix + name
            result.append((full_name, self._parameters[name]))

        for name in self._layers:
            child_prefix = prefix + name + "."
            child = self._layers[name].named_parameters(child_prefix)
            for item in child:
                result.append(item)

        return result

    def parameter_count(self):
        total = 0
        for parameter in self.parameters():
            total += parameter.element_count()
        return total

    def zero_grad(self):
        for parameter in self.parameters():
            parameter.zero_grad()
        return self

    def train(self):
        self.training = True
        for name in self._layers:
            self._layers[name].train()
        return self

    def eval(self):
        self.training = False
        for name in self._layers:
            self._layers[name].eval()
        return self

    def state_dict(self):
        state = {}
        for name, parameter in self.named_parameters():
            state[name] = {
                "shape": list(parameter.shape),
                "data": parameter.data.flatten(),
            }
        return state

    def load_state_dict(self, state, strict=True):
        if not isinstance(state, dict):
            raise TypeError("state must be dict")

        current = {}
        for name, parameter in self.named_parameters():
            current[name] = parameter

        if strict:
            for name in current:
                if name not in state:
                    raise KeyError("missing parameter: " + name)
            for name in state:
                if name not in current:
                    raise KeyError("unexpected parameter: " + name)

        for name in current:
            if name not in state:
                continue

            row = state[name]
            if not isinstance(row, dict):
                raise TypeError("state entry must be dict")

            shape = row.get("shape")
            data = row.get("data")

            if shape is None or data is None:
                raise ValueError("state entry requires shape and data")

            tensor = Tensor(data, shape)
            current[name].set_data(tensor)

        return self

    def forward(self, *args):
        raise NotImplementedError("forward() must be implemented by child layer")

    def __call__(self, *args):
        return self.forward(*args)
