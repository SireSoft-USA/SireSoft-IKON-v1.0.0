# SireLLM Frontend

This folder is the browser-facing shell for SireLLM.

## Architecture

The frontend intentionally stays dependency-free. It uses:

- semantic HTML
- handwritten CSS
- browser-native JavaScript modules
- `fetch` for HTTP requests
- browser streaming primitives where supported

No React, Vue, Angular, jQuery, Bootstrap, Tailwind runtime, CDN script,
hosted chatbot SDK, or external LLM client is required.

## Planned subfolders

```text
frontend/
├── index.html
├── README.md
├── test_frontend_shell.py
├── css/
│   └── app.css
├── js/
│   ├── api.js
│   ├── state.js
│   ├── stream.js
│   ├── chat.js
│   └── app.js
└── assets/
```

The later frontend folders provide styling, API transport, client state,
stream handling, chat rendering, and local static assets.

## Backend contract

The browser application is designed to call the SireLLM HTTP/API gateway
rather than importing backend Python code. The client-side transport module
owns endpoint mapping and can adapt to the runtime server configuration
without coupling the HTML shell to a hard-coded host.

## Accessibility

The document includes:

- a skip link
- semantic `header`, `main`, `aside`, `section`, `footer`
- form labels
- ARIA live regions for runtime status, conversation updates and notices
- keyboard-native controls
- no inline JavaScript handlers
