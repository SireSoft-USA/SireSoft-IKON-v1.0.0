export function chunkText(
  text,
  {
    minChunk = 10,
    maxChunk = 34,
  } = {},
) {
  if (typeof text !== "string") {
    throw new TypeError(
      "text must be a string",
    );
  }

  if (
    !Number.isInteger(minChunk)
    || !Number.isInteger(maxChunk)
    || minChunk <= 0
    || maxChunk < minChunk
  ) {
    throw new RangeError(
      "invalid chunk bounds",
    );
  }

  const chunks = [];
  let start = 0;

  while (start < text.length) {
    let end = Math.min(
      text.length,
      start + maxChunk,
    );

    if (end < text.length) {
      const floor = Math.min(
        text.length,
        start + minChunk,
      );

      let split = end;

      while (
        split > floor
        && !/\s/.test(
          text[split],
        )
      ) {
        split -= 1;
      }

      if (split > floor) {
        end = split + 1;
      }
    }

    chunks.push(
      text.slice(
        start,
        end,
      ),
    );

    start = end;
  }

  return chunks;
}

export async function progressiveText(
  text,
  {
    onChunk,
    delayMs = 0,
    signal = null,
  } = {},
) {
  if (
    typeof onChunk
    !== "function"
  ) {
    throw new TypeError(
      "onChunk must be a function",
    );
  }

  const chunks = chunkText(
    text,
  );

  for (
    const chunk
    of chunks
  ) {
    if (
      signal
      && signal.aborted
    ) {
      throw new DOMException(
        "Progressive rendering aborted",
        "AbortError",
      );
    }

    onChunk(
      chunk,
    );

    if (delayMs > 0) {
      await new Promise(
        (resolve) => {
          setTimeout(
            resolve,
            delayMs,
          );
        },
      );
    } else {
      await Promise.resolve();
    }
  }

  return text;
}
