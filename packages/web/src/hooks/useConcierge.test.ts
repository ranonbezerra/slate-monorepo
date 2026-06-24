import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ConciergeEvent } from "../types/concierge";
import { useConcierge } from "./useConcierge";

const streamConcierge = vi.fn();

vi.mock("../lib/concierge-api", () => ({
	streamConcierge: (...args: unknown[]) => streamConcierge(...args),
}));

async function* events(items: ConciergeEvent[]): AsyncGenerator<ConciergeEvent> {
	for (const item of items) yield item;
}

afterEach(() => {
	streamConcierge.mockReset();
});

describe("useConcierge", () => {
	it("appends the user message and streams the assistant reply", async () => {
		streamConcierge.mockReturnValue(
			events([{ delta: "Play " }, { delta: "Hollow Knight." }, { done: true, thread_id: "t1" }]),
		);

		const { result } = renderHook(() => useConcierge());

		await act(async () => {
			await result.current.send("what should I play?");
		});

		expect(result.current.messages).toEqual([
			{ role: "user", text: "what should I play?" },
			{ role: "assistant", text: "Play Hollow Knight." },
		]);
		expect(result.current.isStreaming).toBe(false);
		expect(result.current.error).toBeNull();
	});

	it("threads the server thread_id into the next turn", async () => {
		streamConcierge
			.mockReturnValueOnce(events([{ delta: "Hi." }, { done: true, thread_id: "thread-42" }]))
			.mockReturnValueOnce(events([{ delta: "Again." }, { done: true, thread_id: "thread-42" }]));

		const { result } = renderHook(() => useConcierge());

		await act(async () => {
			await result.current.send("first");
		});
		await act(async () => {
			await result.current.send("second");
		});

		expect(streamConcierge).toHaveBeenNthCalledWith(1, "first", undefined);
		expect(streamConcierge).toHaveBeenNthCalledWith(2, "second", "thread-42");
	});

	it("ignores empty input", async () => {
		const { result } = renderHook(() => useConcierge());
		await act(async () => {
			await result.current.send("   ");
		});
		expect(result.current.messages).toEqual([]);
		expect(streamConcierge).not.toHaveBeenCalled();
	});

	it("surfaces a server error event", async () => {
		streamConcierge.mockReturnValue(
			events([
				{ error: "The concierge is unavailable right now." },
				{ done: true, thread_id: "t1" },
			]),
		);

		const { result } = renderHook(() => useConcierge());
		await act(async () => {
			await result.current.send("hello");
		});

		expect(result.current.error).toBe("The concierge is unavailable right now.");
		expect(result.current.messages.at(-1)?.text).toContain("unavailable");
	});

	it("surfaces an error when the stream throws", async () => {
		streamConcierge.mockImplementation(() => {
			throw new Error("boom");
		});

		const { result } = renderHook(() => useConcierge());
		await act(async () => {
			await result.current.send("hello");
		});

		await waitFor(() => expect(result.current.error).not.toBeNull());
		const last = result.current.messages.at(-1);
		expect(last?.role).toBe("assistant");
		expect(last?.text).toContain("something went wrong");
	});
});
