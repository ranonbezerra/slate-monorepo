import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { LetMeCarryEvent } from "../types/let-me-carry";
import { useLetMeCarry } from "./useLetMeCarry";

const streamLetMeCarry = vi.fn();

vi.mock("../lib/let-me-carry-api", () => ({
	streamLetMeCarry: (...args: unknown[]) => streamLetMeCarry(...args),
}));

async function* events(items: LetMeCarryEvent[]): AsyncGenerator<LetMeCarryEvent> {
	for (const item of items) yield item;
}

afterEach(() => {
	streamLetMeCarry.mockReset();
});

describe("useLetMeCarry", () => {
	it("appends the user message and streams the assistant reply token by token", async () => {
		streamLetMeCarry.mockReturnValue(
			events([{ token: "Play " }, { token: "Hollow Knight." }, { done: true, thread_id: "t1" }]),
		);

		const { result } = renderHook(() => useLetMeCarry());

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

	it("attaches a validated recommendation and tracks the active tool", async () => {
		streamLetMeCarry.mockReturnValue(
			events([
				{ tool: "search_library", phase: "start" },
				{ tool: "search_library", phase: "end" },
				{ token: "Give this a go." },
				{ recommendation: { id: "abc", title: "Hades" } },
				{ done: true, thread_id: "t1" },
			]),
		);

		const { result } = renderHook(() => useLetMeCarry());
		await act(async () => {
			await result.current.send("what should I play?");
		});

		const last = result.current.messages.at(-1);
		expect(last?.text).toBe("Give this a go.");
		expect(last?.recommendation).toEqual({ id: "abc", title: "Hades" });
		expect(result.current.activeTool).toBeNull(); // cleared once the turn ends
	});

	it("appends a degrade nudge to the prose", async () => {
		streamLetMeCarry.mockReturnValue(
			events([
				{ token: "Hmm." },
				{ degrade: "I'm not certain that one's in your library." },
				{ done: true, thread_id: "t1" },
			]),
		);

		const { result } = renderHook(() => useLetMeCarry());
		await act(async () => {
			await result.current.send("play something");
		});

		expect(result.current.messages.at(-1)?.text).toContain("not certain");
	});

	it("threads the server thread_id into the next turn", async () => {
		streamLetMeCarry
			.mockReturnValueOnce(events([{ token: "Hi." }, { done: true, thread_id: "thread-42" }]))
			.mockReturnValueOnce(events([{ token: "Again." }, { done: true, thread_id: "thread-42" }]));

		const { result } = renderHook(() => useLetMeCarry());

		await act(async () => {
			await result.current.send("first");
		});
		await act(async () => {
			await result.current.send("second");
		});

		expect(streamLetMeCarry).toHaveBeenNthCalledWith(
			1,
			"first",
			undefined,
			expect.any(AbortSignal),
		);
		expect(streamLetMeCarry).toHaveBeenNthCalledWith(
			2,
			"second",
			"thread-42",
			expect.any(AbortSignal),
		);
	});

	it("ignores empty input", async () => {
		const { result } = renderHook(() => useLetMeCarry());
		await act(async () => {
			await result.current.send("   ");
		});
		expect(result.current.messages).toEqual([]);
		expect(streamLetMeCarry).not.toHaveBeenCalled();
	});

	it("cancelling mid-stream keeps the partial reply without an error", async () => {
		// Stream one token, then park until the abort signal fires (rejecting
		// like an aborted fetch would).
		streamLetMeCarry.mockImplementation((_msg: string, _tid: undefined, signal: AbortSignal) =>
			(async function* () {
				yield { token: "partial " };
				await new Promise((_resolve, reject) => {
					signal.addEventListener("abort", () =>
						reject(Object.assign(new Error("aborted"), { name: "AbortError" })),
					);
				});
			})(),
		);

		const { result } = renderHook(() => useLetMeCarry());
		let sendPromise: Promise<void> = Promise.resolve();
		await act(async () => {
			sendPromise = result.current.send("what should I play?");
			await Promise.resolve(); // let the first token flush
		});
		await act(async () => {
			result.current.cancel();
			await sendPromise;
		});

		expect(result.current.error).toBeNull();
		expect(result.current.isStreaming).toBe(false);
		expect(result.current.messages.at(-1)?.text).toContain("partial");
	});

	it("surfaces a server error event", async () => {
		streamLetMeCarry.mockReturnValue(
			events([
				{ error: "The let_me_carry is unavailable right now." },
				{ done: true, thread_id: "t1" },
			]),
		);

		const { result } = renderHook(() => useLetMeCarry());
		await act(async () => {
			await result.current.send("hello");
		});

		expect(result.current.error).toBe("The let_me_carry is unavailable right now.");
		expect(result.current.messages.at(-1)?.text).toContain("unavailable");
	});

	it("surfaces an error when the stream throws", async () => {
		streamLetMeCarry.mockImplementation(() => {
			throw new Error("boom");
		});

		const { result } = renderHook(() => useLetMeCarry());
		await act(async () => {
			await result.current.send("hello");
		});

		await waitFor(() => expect(result.current.error).not.toBeNull());
		const last = result.current.messages.at(-1);
		expect(last?.role).toBe("assistant");
		expect(last?.text).toContain("something went wrong");
	});
});
