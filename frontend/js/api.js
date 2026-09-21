const DEFAULT_TIMEOUT_MS = 30000;

export class APIError extends Error {
  constructor(
    message,
    {
      status = 0,
      code = "CLIENT_ERROR",
      details = {},
      retryable = false,
      traceId = null,
    } = {},
  ) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.retryable = Boolean(retryable);
    this.traceId = traceId;
  }
}

function normalizeBaseURL(baseURL) {
  if (baseURL === null || baseURL === undefined) {
    return "";
  }

  if (typeof baseURL !== "string") {
    throw new TypeError("baseURL must be a string");
  }

  const trimmed = baseURL.trim();

  if (trimmed === "" || trimmed === "/") {
    return "";
  }

  return trimmed.endsWith("/")
    ? trimmed.slice(0, -1)
    : trimmed;
}

function timeoutSignal(timeoutMs) {
  if (
    !Number.isInteger(timeoutMs)
    || timeoutMs <= 0
  ) {
    throw new RangeError(
      "timeoutMs must be a positive integer",
    );
  }

  const controller = new AbortController();
  const timer = setTimeout(
    () => controller.abort(
      new DOMException(
        "Request timed out",
        "TimeoutError",
      ),
    ),
    timeoutMs,
  );

  return {
    controller,
    cancel() {
      clearTimeout(timer);
    },
  };
}

function requestId(prefix = "web") {
  if (
    typeof crypto !== "undefined"
    && typeof crypto.randomUUID === "function"
  ) {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.floor(
    Math.random() * 1000000,
  )}`;
}

export class SireLLMClient {
  constructor({
    baseURL = "",
    timeoutMs = DEFAULT_TIMEOUT_MS,
  } = {}) {
    this.baseURL = normalizeBaseURL(baseURL);
    this.timeoutMs = timeoutMs;
  }

  async health() {
    return this.request(
      "GET",
      "/v1/health",
    );
  }

  async chat(
    query,
    {
      maxNewTokens = 64,
      candidateK = 20,
      topK = 5,
      useMMR = true,
      mmrLambda = 0.75,
      similarityWeight = 1.0,
      sampler = "greedy",
      seed = 1337,
      temperature = 1.0,
      topPSampling = null,
      repetitionPenalty = 1.0,
      signal = null,
    } = {},
  ) {
    if (
      typeof query !== "string"
      || query.trim() === ""
    ) {
      throw new TypeError(
        "query must be a non-empty string",
      );
    }

    const payload = {
      query: query.trim(),
      max_new_tokens: maxNewTokens,
      candidate_k: candidateK,
      top_k: topK,
      use_mmr: Boolean(useMMR),
      mmr_lambda: mmrLambda,
      similarity_weight: similarityWeight,
      sampler,
      seed,
      temperature,
      top_p: topPSampling,
      repetition_penalty: repetitionPenalty,
    };

    return this.request(
      "POST",
      "/v1/chat",
      {
        body: payload,
        signal,
      },
    );
  }

  async request(
    method,
    path,
    {
      body = null,
      headers = {},
      signal = null,
    } = {},
  ) {
    if (
      typeof method !== "string"
      || method.trim() === ""
    ) {
      throw new TypeError(
        "method must be a non-empty string",
      );
    }

    if (
      typeof path !== "string"
      || !path.startsWith("/")
    ) {
      throw new TypeError(
        "path must start with /",
      );
    }

    const timer = timeoutSignal(
      this.timeoutMs,
    );

    const controller = timer.controller;

    const onAbort = () => {
      if (!controller.signal.aborted) {
        controller.abort(
          signal.reason
          ?? new DOMException(
            "Request aborted",
            "AbortError",
          ),
        );
      }
    };

    if (signal) {
      if (signal.aborted) {
        onAbort();
      } else {
        signal.addEventListener(
          "abort",
          onAbort,
          {
            once: true,
          },
        );
      }
    }

    const normalizedHeaders = {
      Accept: "application/json",
      "X-Trace-Id": requestId(
        "trace",
      ),
      "X-Correlation-Id": requestId(
        "corr",
      ),
      ...headers,
    };

    const options = {
      method: method.toUpperCase(),
      headers: normalizedHeaders,
      signal: controller.signal,
      cache: "no-store",
      credentials: "same-origin",
    };

    if (body !== null) {
      normalizedHeaders[
        "Content-Type"
      ] = "application/json";

      options.body = JSON.stringify(
        body,
      );
    }

    try {
      const response = await fetch(
        this.baseURL + path,
        options,
      );

      const contentType = (
        response.headers.get(
          "content-type",
        )
        ?? ""
      ).toLowerCase();

      if (
        !contentType.includes(
          "application/json",
        )
      ) {
        throw new APIError(
          "SireLLM returned a non-JSON response",
          {
            status: response.status,
            code: "INVALID_HTTP_RESPONSE",
          },
        );
      }

      const envelope = await response.json();

      if (
        !envelope
        || typeof envelope !== "object"
      ) {
        throw new APIError(
          "SireLLM returned an invalid response envelope",
          {
            status: response.status,
            code: "INVALID_HTTP_RESPONSE",
          },
        );
      }

      if (
        response.ok
        && envelope.ok === true
      ) {
        return envelope;
      }

      const error = (
        envelope.error
        && typeof envelope.error
        === "object"
      )
        ? envelope.error
        : {};

      throw new APIError(
        error.message
          ?? "SireLLM request failed",
        {
          status: (
            envelope.status
            ?? response.status
          ),
          code: (
            error.code
            ?? "REQUEST_FAILED"
          ),
          details: (
            error.details
            ?? {}
          ),
          retryable: (
            error.retryable
            ?? false
          ),
          traceId: (
            envelope.trace_id
            ?? null
          ),
        },
      );
    } catch (error) {
      if (
        error instanceof APIError
      ) {
        throw error;
      }

      if (
        error
        && error.name
        === "AbortError"
      ) {
        throw new APIError(
          "Request was cancelled",
          {
            code: "REQUEST_ABORTED",
            retryable: true,
          },
        );
      }

      if (
        error
        && error.name
        === "TimeoutError"
      ) {
        throw new APIError(
          "SireLLM request timed out",
          {
            code: "REQUEST_TIMEOUT",
            retryable: true,
          },
        );
      }

      throw new APIError(
        "Unable to reach the SireLLM runtime",
        {
          code: "NETWORK_ERROR",
          retryable: true,
          details: {
            cause: String(
              error?.message
              ?? error,
            ),
          },
        },
      );
    } finally {
      timer.cancel();

      if (signal) {
        signal.removeEventListener(
          "abort",
          onAbort,
        );
      }
    }
  }
}

export function createSireLLMClient(
  options = {},
) {
  return new SireLLMClient(
    options,
  );
}
