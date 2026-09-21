import {
  APIError,
  createSireLLMClient,
} from "./api.js";

import {
  createStore,
  nextSessionId,
  normalizeCitations,
} from "./state.js";

import {
  progressiveText,
} from "./stream.js";

import {
  ChatView,
} from "./chat.js";


const client = (
  createSireLLMClient()
);

const store = createStore();
const view = new ChatView();

let activeController = null;

function setHealth(
  {
    state,
    text,
    ready,
  },
) {
  store.setState(
    (
      current,
    ) => ({
      ...current,
      health: {
        state,
        text,
        ready,
      },
    }),
  );
}

function startSession() {
  const sessionId = nextSessionId();

  store.setState(
    (
      current,
    ) => ({
      ...current,
      sessionId,
      messages: [],
      citations: [],
      lastError: null,
    }),
  );

  view.clearConversation();

  view.appendMessage({
    role: "assistant",
    text: (
      "New SireLLM session started. "
      + "Ask a SireSoft question when ready."
    ),
  });

  view.focusInput();
}

function clearConversation() {
  store.setState(
    (
      current,
    ) => ({
      ...current,
      messages: [],
      citations: [],
      lastError: null,
    }),
  );

  view.clearConversation();

  view.appendMessage({
    role: "assistant",
    text: (
      "Conversation cleared. "
      + "The current session remains active."
    ),
  });

  view.focusInput();
}

function answerObject(
  envelope,
) {
  const answer = (
    envelope
    && envelope.data
    && envelope.data.answer
  );

  if (
    !answer
    || typeof answer
    !== "object"
  ) {
    throw new APIError(
      "Chat response did not contain an answer object",
      {
        code: (
          "INVALID_CHAT_RESPONSE"
        ),
      },
    );
  }

  return answer;
}

async function submitMessage(
  rawValue,
) {
  const text = (
    typeof rawValue
    === "string"
      ? rawValue.trim()
      : ""
  );

  if (text === "") {
    view.toast(
      "Enter a message first.",
      "error",
    );

    return;
  }

  if (
    !store.getState()
    .health.ready
  ) {
    view.toast(
      "SireLLM runtime is not ready yet.",
      "error",
    );

    return;
  }

  if (
    store.getState()
    .sessionId === null
  ) {
    startSession();
  }

  if (activeController) {
    activeController.abort();
  }

  activeController = (
    new AbortController()
  );

  const userMessage = {
    role: "user",
    text,
  };

  store.setState(
    (
      current,
    ) => ({
      ...current,
      busy: true,
      lastError: null,
      messages: [
        ...current.messages,
        userMessage,
      ],
    }),
  );

  view.appendMessage(
    userMessage,
  );

  view.setInput("");

  const assistantNode = (
    view.appendMessage({
      role: "assistant",
      text: "",
    })
  );

  try {
    const envelope = await client.chat(
      text,
      {
        signal: (
          activeController.signal
        ),
      },
    );

    const answer = answerObject(
      envelope,
    );

    if (
      answer.status
      === "blocked"
    ) {
      assistantNode.paragraph.textContent = (
        "This request was blocked by SireLLM guardrails."
      );

      store.setState(
        (
          current,
        ) => ({
          ...current,
          busy: false,
          citations: [],
          messages: [
            ...current.messages,
            {
              role: "assistant",
              text: (
                assistantNode
                .paragraph
                .textContent
              ),
              blocked: true,
            },
          ],
        }),
      );

      return;
    }

    const answerText = (
      typeof answer.answer_text
      === "string"
      && answer.answer_text !== ""
        ? answer.answer_text
        : "SireLLM returned an empty answer."
    );

    const citations = normalizeCitations(
      answer.citations,
    );

    await progressiveText(
      answerText,
      {
        signal: (
          activeController.signal
        ),
        onChunk(
          chunk,
        ) {
          assistantNode.paragraph.textContent += chunk;
          view.scrollToLatest();
        },
      },
    );

    view.appendCitationButtons(
      assistantNode.content,
      citations,
      (
        citation,
      ) => {
        view.showCitations([
          citation,
        ]);
      },
    );

    store.setState(
      (
        current,
      ) => ({
        ...current,
        busy: false,
        citations,
        messages: [
          ...current.messages,
          {
            role: "assistant",
            text: answerText,
            citations,
            traceId: (
              envelope.trace_id
              ?? null
            ),
          },
        ],
      }),
    );
  } catch (error) {
    const message = (
      error instanceof APIError
        ? error.message
        : "Unexpected chat error"
    );

    assistantNode.article.classList.add(
      "message-error",
    );

    assistantNode.paragraph.textContent = (
      message
    );

    store.setState(
      (
        current,
      ) => ({
        ...current,
        busy: false,
        lastError: {
          message,
          code: (
            error?.code
            ?? "CLIENT_ERROR"
          ),
        },
      }),
    );

    view.toast(
      message,
      "error",
    );
  } finally {
    activeController = null;
  }
}

async function checkHealth() {
  setHealth({
    state: "connecting",
    text: "Connecting",
    ready: false,
  });

  try {
    const envelope = await client.health();

    const health = (
      envelope
      && envelope.data
      && (
        envelope.data.health
        ?? envelope.data.status
      )
    );

    const ready = (
      health
      && typeof health
      === "object"
      && (
        health.ready === true
        || health.status === "healthy"
      )
    );

    setHealth({
      state: (
        ready
          ? "ready"
          : "error"
      ),
      text: (
        ready
          ? "Runtime ready"
          : "Runtime unavailable"
      ),
      ready,
    });
  } catch (error) {
    setHealth({
      state: "error",
      text: "Runtime unavailable",
      ready: false,
    });
  }
}

store.subscribe(
  (
    state,
  ) => {
    view.renderState(
      state,
    );
  },
);

view.bind({
  onSubmit: submitMessage,
  onNewChat: startSession,
  onClearChat: clearConversation,
  onCloseCitations() {
    view.closeCitations();
  },
});

view.renderState(
  store.getState(),
);

startSession();
checkHealth();
