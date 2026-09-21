class RuntimeContext:
    def __init__(self):
        self._values = {}
        self._order = []
        self._sealed = False

    def register(self, name, value):
        if self._sealed:
            raise RuntimeError("runtime context is sealed")

        if not isinstance(name, str) or name == "":
            raise ValueError("context name must be non-empty str")

        if name in self._values:
            raise ValueError(
                "runtime context value already registered: " + name
            )

        self._values[name] = value
        self._order.append(name)

        return value

    def get(self, name):
        if name not in self._values:
            raise KeyError(
                "runtime context value not found: " + str(name)
            )

        return self._values[name]

    def has(self, name):
        return name in self._values

    def names(self):
        return list(self._order)

    def seal(self):
        self._sealed = True
        return self

    def sealed(self):
        return self._sealed

    def summary(self):
        return {
            "sealed": self._sealed,
            "names": list(self._order),
            "count": len(self._order),
        }
