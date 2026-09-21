class RoundRobinStrategy:
    """
    Service-local deterministic round-robin selection.
    """

    def __init__(self):
        self._positions = {}

    def select(
        self,
        service_name,
        instances,
        excluded_ids=None,
    ):
        candidates = self._candidates(
            instances,
            excluded_ids,
        )

        if len(candidates) == 0:
            return None

        position = self._positions.get(
            service_name,
            0,
        )

        selected = candidates[
            position % len(candidates)
        ]

        self._positions[
            service_name
        ] = (
            position + 1
        )

        return selected

    def reset(
        self,
        service_name=None,
    ):
        if service_name is None:
            self._positions = {}
        elif service_name in self._positions:
            del self._positions[
                service_name
            ]

        return self

    def _candidates(
        self,
        instances,
        excluded_ids,
    ):
        if excluded_ids is None:
            excluded_ids = {}

        result = []

        for instance in instances:
            if (
                instance.available()
                and instance.instance_id
                not in excluded_ids
            ):
                result.append(
                    instance
                )

        return result


class LeastLoadStrategy:
    """
    Chooses the available instance with the smallest active-request count.

    Registration order is the deterministic tie-break.
    """

    def select(
        self,
        service_name,
        instances,
        excluded_ids=None,
    ):
        if excluded_ids is None:
            excluded_ids = {}

        best = None
        best_load = None

        for instance in instances:
            if not instance.available():
                continue

            if instance.instance_id in excluded_ids:
                continue

            load = instance.load_score()

            if (
                best is None
                or load < best_load
            ):
                best = instance
                best_load = load

        return best


class AdaptiveStrategy:
    """
    Uses least-load when load differs; round-robin for equal-load peers.
    """

    def __init__(self):
        self._round_robin = RoundRobinStrategy()

    def select(
        self,
        service_name,
        instances,
        excluded_ids=None,
    ):
        if excluded_ids is None:
            excluded_ids = {}

        available = []

        for instance in instances:
            if (
                instance.available()
                and instance.instance_id
                not in excluded_ids
            ):
                available.append(
                    instance
                )

        if len(available) == 0:
            return None

        minimum = None

        for instance in available:
            load = instance.load_score()

            if minimum is None or load < minimum:
                minimum = load

        least_loaded = []

        for instance in available:
            if instance.load_score() == minimum:
                least_loaded.append(
                    instance
                )

        return self._round_robin.select(
            service_name,
            least_loaded,
            excluded_ids={},
        )
