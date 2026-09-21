function clone(value) {
  if (
    value === null
    || typeof value !== "object"
  ) {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map(clone);
  }

  const result = {};

  for (
    const key
    of Object.keys(value)
  ) {
    result[key] = clone(
      value[key],
    );
  }

  return result;
}

function freeze(value) {
  if (
    value === null
    || typeof value !== "object"
    || Object.isFrozen(value)
  ) {
    return value;
  }

  Object.freeze(value);

  for (
    const key
    of Object.keys(value)
  ) {
    freeze(
      value[key],
    );
  }

  return value;
}

export function createInitialState() {
  return freeze({
    sessionId: null,
    messages: [],
    citations: [],
    health: {
      state: "connecting",
      text: "Connecting",
      ready: false,
    },
    busy: false,
    lastError: null,
  });
}

export function createStore(
  initialState = createInitialState(),
) {
  let state = freeze(
    clone(initialState),
  );

  const listeners = new Set();

  function notify() {
    for (
      const listener
      of listeners
    ) {
      listener(state);
    }
  }

  return {
    getState() {
      return state;
    },

    setState(
      updater,
    ) {
      if (
        typeof updater
        !== "function"
      ) {
        throw new TypeError(
          "state updater must be a function",
        );
      }

      const next = updater(
        clone(state),
      );

      if (
        !next
        || typeof next !== "object"
      ) {
        throw new TypeError(
          "state updater must return an object",
        );
      }

      state = freeze(
        clone(next),
      );

      notify();
      return state;
    },

    subscribe(
      listener,
    ) {
      if (
        typeof listener
        !== "function"
      ) {
        throw new TypeError(
          "listener must be a function",
        );
      }

      listeners.add(
        listener,
      );

      return () => {
        listeners.delete(
          listener,
        );
      };
    },
  };
}

export function nextSessionId() {
  if (
    typeof crypto !== "undefined"
    && typeof crypto.randomUUID
    === "function"
  ) {
    return (
      "session-"
      + crypto.randomUUID()
    );
  }

  return (
    "session-"
    + Date.now()
    + "-"
    + Math.floor(
      Math.random() * 1000000,
    )
  );
}

export function normalizeCitations(
  citations,
) {
  if (!Array.isArray(citations)) {
    return [];
  }

  return citations
    .filter(
      (
        item,
      ) => (
        item
        && typeof item
        === "object"
      ),
    )
    .map(
      (
        item,
        index,
      ) => ({
        id: (
          item.citation_id
          ?? item.chunk_id
          ?? `citation-${index + 1}`
        ),
        title: (
          item.title
          ?? item.document_id
          ?? item.source_record_id
          ?? `Source ${index + 1}`
        ),
        text: (
          item.text
          ?? item.snippet
          ?? item.content
          ?? ""
        ),
        score: (
          typeof item.score
          === "number"
            ? item.score
            : null
        ),
        metadata: (
          item.metadata
          && typeof item.metadata
          === "object"
            ? clone(
                item.metadata,
              )
            : {}
        ),
      }),
    );
}
