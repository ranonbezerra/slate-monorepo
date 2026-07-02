import { fetchWithAuthRetry } from "@slate/shared/api";
import type { LetMeCarryEvent } from "../types/let-me-carry";

// ---------------------------------------------------------------------------
// let_me_carry chat — consumes the SSE endpoint as an async generator
// (ROADMAP Epic 16). The endpoint streams typed events as the turn generates:
// `token` (prose), `tool` (+`phase`), `recommendation`, `degrade`, `error`,
// then a final `done` carrying the `thread_id` for the next turn.
// ---------------------------------------------------------------------------

export async function* streamLetMeCarry(
	message: string,
	threadId?: string,
	signal?: AbortSignal,
): AsyncGenerator<LetMeCarryEvent> {
	const res = await fetchWithAuthRetry("/v1/let_me_carry/chat", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ message, thread_id: threadId }),
		signal,
	});

	if (!res.ok) {
		throw new Error(`LetMeCarry request failed (${res.status})`);
	}
	if (!res.body) {
		throw new Error("LetMeCarry response had no body");
	}

	const reader = res.body.getReader();
	const decoder = new TextDecoder();
	let buffer = "";

	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			buffer += decoder.decode(value, { stream: true });
			// SSE events are separated by a blank line; process complete lines.
			const lines = buffer.split("\n");
			buffer = lines.pop() ?? "";

			for (const line of lines) {
				const trimmed = line.trim();
				if (!trimmed.startsWith("data:")) continue;
				const payload = trimmed.slice("data:".length).trim();
				if (!payload) continue;
				try {
					yield JSON.parse(payload) as LetMeCarryEvent;
				} catch {
					// Skip malformed events rather than aborting the stream.
				}
			}
		}
	} finally {
		reader.releaseLock();
	}
}
