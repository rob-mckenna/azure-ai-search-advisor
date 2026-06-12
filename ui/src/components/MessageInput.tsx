import { useState } from "react";

interface MessageInputProps {
  onSend: (message: string) => Promise<void> | void;
  disabled?: boolean;
}

export default function MessageInput({ onSend, disabled = false }: MessageInputProps) {
  const [value, setValue] = useState("");

  const submit = async () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) {
      return;
    }

    setValue("");
    await onSend(trimmed);
  };

  return (
    <div className="message-input-wrap">
      <label className="sr-only" htmlFor="chat-message-input">
        Ask the advisor a question
      </label>
      <textarea
        id="chat-message-input"
        className="message-input"
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void submit();
          }
        }}
        placeholder="Ask about replicas, partitions, pricing, semantic search, or recommendations..."
        rows={3}
        value={value}
      />
      <button className="primary-button" disabled={disabled || value.trim().length === 0} onClick={() => void submit()} type="button">
        Send
      </button>
    </div>
  );
}
