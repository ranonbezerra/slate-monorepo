export type ChatRole = "user" | "assistant";

export interface ChatMessage {
	role: ChatRole;
	text: string;
}

// One Server-Sent Event from POST /v1/concierge/chat.
export interface ConciergeEvent {
	delta?: string;
	error?: string;
	done?: boolean;
	thread_id?: string;
}
