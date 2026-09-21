function requiredElement(
  root,
  id,
) {
  const element = root.getElementById(
    id,
  );

  if (!element) {
    throw new Error(
      "Missing frontend element: "
      + id,
    );
  }

  return element;
}

function clearChildren(node) {
  while (node.firstChild) {
    node.removeChild(
      node.firstChild,
    );
  }
}

function roleLabel(role) {
  if (role === "user") {
    return "You";
  }

  if (role === "assistant") {
    return "SL";
  }

  return "!";
}

export class ChatView {
  constructor(
    documentRef = document,
  ) {
    this.document = documentRef;

    this.elements = {
      form: requiredElement(
        documentRef,
        "chat-form",
      ),
      input: requiredElement(
        documentRef,
        "message-input",
      ),
      send: requiredElement(
        documentRef,
        "send-button",
      ),
      newChat: requiredElement(
        documentRef,
        "new-chat-button",
      ),
      clearChat: requiredElement(
        documentRef,
        "clear-chat-button",
      ),
      closeCitations: requiredElement(
        documentRef,
        "close-citations-button",
      ),
      messageList: requiredElement(
        documentRef,
        "message-list",
      ),
      citationPanel: requiredElement(
        documentRef,
        "citation-panel",
      ),
      citationList: requiredElement(
        documentRef,
        "citation-list",
      ),
      sessionId: requiredElement(
        documentRef,
        "session-id",
      ),
      statusIndicator: requiredElement(
        documentRef,
        "status-indicator",
      ),
      statusText: requiredElement(
        documentRef,
        "status-text",
      ),
      buildStatus: requiredElement(
        documentRef,
        "build-status",
      ),
      toastRegion: requiredElement(
        documentRef,
        "toast-region",
      ),
    };
  }

  bind({
    onSubmit,
    onNewChat,
    onClearChat,
    onCloseCitations,
  }) {
    this.elements.form.addEventListener(
      "submit",
      (
        event,
      ) => {
        event.preventDefault();

        onSubmit(
          this.elements.input.value,
        );
      },
    );

    this.elements.newChat.addEventListener(
      "click",
      onNewChat,
    );

    this.elements.clearChat.addEventListener(
      "click",
      onClearChat,
    );

    this.elements.closeCitations.addEventListener(
      "click",
      onCloseCitations,
    );

    this.elements.input.addEventListener(
      "keydown",
      (
        event,
      ) => {
        if (
          event.key === "Enter"
          && !event.shiftKey
        ) {
          event.preventDefault();
          this.elements.form.requestSubmit();
        }
      },
    );
  }

  renderState(
    state,
  ) {
    this.elements.sessionId.textContent = (
      state.sessionId
      ?? "Not started"
    );

    this.elements.statusText.textContent = (
      state.health.text
    );

    this.elements.statusIndicator.dataset.state = (
      state.health.state
    );

    this.elements.send.disabled = (
      Boolean(
        state.busy,
      )
      || !state.health.ready
    );

    this.elements.input.disabled = Boolean(
      state.busy,
    );

    this.elements.buildStatus.textContent = (
      state.health.ready
        ? "Runtime ready."
        : "Runtime not ready."
    );
  }

  clearConversation() {
    clearChildren(
      this.elements.messageList,
    );

    this.closeCitations();
  }

  appendMessage({
    role,
    text = "",
    error = false,
  }) {
    const article = (
      this.document
      .createElement(
        "article",
      )
    );

    article.className = (
      "message message-"
      + role
      + (
        error
          ? " message-error"
          : ""
      )
    );

    article.dataset.role = role;

    const avatar = (
      this.document
      .createElement(
        "div",
      )
    );

    avatar.className = (
      "message-avatar"
    );

    avatar.setAttribute(
      "aria-hidden",
      "true",
    );

    avatar.textContent = (
      roleLabel(
        role,
      )
    );

    const content = (
      this.document
      .createElement(
        "div",
      )
    );

    content.className = (
      "message-content"
    );

    const paragraph = (
      this.document
      .createElement(
        "p",
      )
    );

    paragraph.textContent = text;
    content.appendChild(
      paragraph,
    );

    article.appendChild(
      avatar,
    );

    article.appendChild(
      content,
    );

    this.elements.messageList.appendChild(
      article,
    );

    this.scrollToLatest();

    return {
      article,
      paragraph,
      content,
    };
  }

  appendCitationButtons(
    messageContent,
    citations,
    onOpen,
  ) {
    if (
      !Array.isArray(citations)
      || citations.length === 0
    ) {
      return;
    }

    const container = (
      this.document
      .createElement(
        "div",
      )
    );

    container.className = (
      "message-citations"
    );

    citations.forEach(
      (
        citation,
        index,
      ) => {
        const button = (
          this.document
          .createElement(
            "button",
          )
        );

        button.type = "button";
        button.className = (
          "citation-chip"
        );
        button.textContent = (
          `Source ${index + 1}`
        );

        button.addEventListener(
          "click",
          () => {
            onOpen(
              citation,
            );
          },
        );

        container.appendChild(
          button,
        );
      },
    );

    messageContent.appendChild(
      container,
    );
  }

  showCitations(
    citations,
  ) {
    clearChildren(
      this.elements.citationList,
    );

    citations.forEach(
      (
        citation,
        index,
      ) => {
        const item = (
          this.document
          .createElement(
            "li",
          )
        );

        const title = (
          this.document
          .createElement(
            "strong",
          )
        );

        title.textContent = (
          citation.title
          || `Source ${index + 1}`
        );

        item.appendChild(
          title,
        );

        if (citation.text) {
          const snippet = (
            this.document
            .createElement(
              "p",
            )
          );

          snippet.textContent = (
            citation.text
          );

          item.appendChild(
            snippet,
          );
        }

        this.elements.citationList.appendChild(
          item,
        );
      },
    );

    this.elements.citationPanel.hidden = (
      citations.length === 0
    );
  }

  closeCitations() {
    this.elements.citationPanel.hidden = true;
  }

  setInput(
    value,
  ) {
    this.elements.input.value = value;
  }

  focusInput() {
    this.elements.input.focus();
  }

  scrollToLatest() {
    const list = (
      this.elements.messageList
    );

    list.scrollTop = (
      list.scrollHeight
    );
  }

  toast(
    message,
    tone = "default",
  ) {
    const item = (
      this.document
      .createElement(
        "div",
      )
    );

    item.className = "toast";
    item.dataset.tone = tone;
    item.textContent = message;

    this.elements.toastRegion.appendChild(
      item,
    );

    setTimeout(
      () => {
        item.remove();
      },
      4500,
    );
  }
}
