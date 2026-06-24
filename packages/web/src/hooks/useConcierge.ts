import { useCallback, useRef, useState } from "react";
import { streamConcierge } from "../lib/concierge-api";
import type { ChatMessage } from "../types/concierge";

// ---------------------------------------------------------------------------
// useConcierge — drives a streaming chat conversation with the Backlog
// Concierge. Appends the assistant's reply token-by-token and threads the
// server-issued thread_id across turns.
// ---------------------------------------------------------------------------

const FALLBACK_ERROR = "Sorry, something went wrong. Please try again.";

export function useConcierge() {
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [isStreaming, setIsStreaming] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const threadId = useRef<string | undefined>(undefined);

	const send = useCallback(
		async (raw: string) => {
			const text = raw.trim();
			if (!text || isStreaming) return;

			setError(null);
			setIsStreaming(true);
			// Append the user message + an empty assistant placeholder to fill in.
			setMessages((prev) => [...prev, { role: "user", text }, { role: "assistant", text: "" }]);

			const setAssistant = (textValue: string) => {
				setMessages((prev) => {
					const next = [...prev];
					next[next.length - 1] = { role: "assistant", text: textValue };
					return next;
				});
			};

			const appendDelta = (delta: string) => {
				setMessages((prev) => {
					const next = [...prev];
					const last = next[next.length - 1];
					next[next.length - 1] = { ...last, text: last.text + delta };
					return next;
				});
			};

			try {
				for await (const event of streamConcierge(text, threadId.current)) {
					if (event.error) {
						setError(event.error);
						setAssistant(event.error);
					}
					if (event.delta) appendDelta(event.delta);
					if (event.done && event.thread_id) threadId.current = event.thread_id;
				}
			} catch {
				setError(FALLBACK_ERROR);
				setAssistant(FALLBACK_ERROR);
			} finally {
				setIsStreaming(false);
			}
		},
		[isStreaming],
	);

	return { messages, isStreaming, error, send } as const;
}
