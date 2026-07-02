import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@slate/shared/api", () => {
	const getAccessToken = vi.fn(() => "test-token" as string | null);
	// Mirror the real fetchWithAuthRetry: prepend BASE_URL, attach the bearer
	// token as a Headers instance, and delegate to the global fetch mock.
	const fetchWithAuthRetry = vi.fn((path: string, init: RequestInit = {}) => {
		const headers = new Headers(init.headers);
		const token = getAccessToken();
		if (token) headers.set("Authorization", `Bearer ${token}`);
		return fetch(`http://test${path}`, { ...init, headers });
	});
	return {
		BASE_URL: "http://test",
		getAccessToken,
		fetchWithAuthRetry,
	};
});

import { getAccessToken } from "@slate/shared/api";
import type { LetMeCarryEvent } from "../types/let-me-carry";
import { streamLetMeCarry } from "./let-me-carry-api";

// ---------------------------------------------------------------------------
// Helpers — build a fake fetch Response whose body streams the given chunks.
// ---------------------------------------------------------------------------

function makeStreamResponse(chunks: string[], init: { ok?: boolean; status?: number } = {}) {
	const encoder = new TextEncoder();
	let i = 0;
	const reader = {
		read: vi.fn(async () => {
			if (i < chunks.length) {
				const value = encoder.encode(chunks[i]);
				i += 1;
				return { done: false, value };
			}
			return { done: true, value: undefined };
		}),
		releaseLock: vi.fn(),
	};
	return {
		ok: init.ok ?? true,
		status: init.status ?? 200,
		body: { getReader: () => reader },
		_reader: reader,
	};
}

async function collect(message: string, threadId?: string): Promise<LetMeCarryEvent[]> {
	const events: LetMeCarryEvent[] = [];
	for await (const event of streamLetMeCarry(message, threadId)) {
		events.push(event);
	}
	return events;
}

const fetchMock = vi.fn();

beforeEach(() => {
	vi.stubGlobal("fetch", fetchMock);
	fetchMock.mockReset();
	(getAccessToken as ReturnType<typeof vi.fn>).mockReturnValue("test-token");
});

afterEach(() => {
	vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Request shape
// ---------------------------------------------------------------------------

describe("streamLetMeCarry request", () => {
	it("POSTs to /v1/let_me_carry/chat with auth header and JSON body", async () => {
		fetchMock.mockResolvedValueOnce(makeStreamResponse(['data: {"done": true}\n']));

		await collect("hello", "thread-7");

		expect(fetchMock).toHaveBeenCalledTimes(1);
		const [url, opts] = fetchMock.mock.calls[0];
		expect(url).toBe("http://test/v1/let_me_carry/chat");
		expect(opts.method).toBe("POST");
		expect((opts.headers as Headers).get("Content-Type")).toBe("application/json");
		expect((opts.headers as Headers).get("Authorization")).toBe("Bearer test-token");
		expect(JSON.parse(opts.body)).toEqual({ message: "hello", thread_id: "thread-7" });
	});

	it("omits the Authorization header when there is no access token", async () => {
		(getAccessToken as ReturnType<typeof vi.fn>).mockReturnValue(null);
		fetchMock.mockResolvedValueOnce(makeStreamResponse(['data: {"done": true}\n']));

		await collect("hi");

		const [, opts] = fetchMock.mock.calls[0];
		expect((opts.headers as Headers).get("Authorization")).toBeNull();
		expect(JSON.parse(opts.body)).toEqual({ message: "hi", thread_id: undefined });
	});
});

// ---------------------------------------------------------------------------
// SSE parsing
// ---------------------------------------------------------------------------

describe("streamLetMeCarry SSE parsing", () => {
	it("parses token events followed by a done event", async () => {
		fetchMock.mockResolvedValueOnce(
			makeStreamResponse([
				'data: {"token": "Hel"}\n',
				'data: {"token": "lo"}\n',
				'data: {"done": true, "thread_id": "abc"}\n',
			]),
		);

		const events = await collect("hi");

		expect(events).toEqual([{ token: "Hel" }, { token: "lo" }, { done: true, thread_id: "abc" }]);
	});

	it("reassembles events split across chunk boundaries", async () => {
		fetchMock.mockResolvedValueOnce(
			makeStreamResponse(['data: {"tok', 'en": "world"}\n', 'data: {"done": true}\n']),
		);

		const events = await collect("hi");

		expect(events).toEqual([{ token: "world" }, { done: true }]);
	});

	it("ignores blank lines and non-data lines", async () => {
		fetchMock.mockResolvedValueOnce(
			makeStreamResponse([
				"\n",
				": keep-alive comment\n",
				"event: message\n",
				'data: {"token": "x"}\n',
				"data: \n",
			]),
		);

		const events = await collect("hi");

		expect(events).toEqual([{ token: "x" }]);
	});

	it("skips malformed JSON without aborting the stream", async () => {
		fetchMock.mockResolvedValueOnce(
			makeStreamResponse(["data: {not valid json}\n", 'data: {"token": "ok"}\n']),
		);

		const events = await collect("hi");

		expect(events).toEqual([{ token: "ok" }]);
	});

	it("surfaces error events from the stream", async () => {
		fetchMock.mockResolvedValueOnce(
			makeStreamResponse(['data: {"error": "blocked"}\n', 'data: {"done": true}\n']),
		);

		const events = await collect("hi");

		expect(events).toEqual([{ error: "blocked" }, { done: true }]);
	});

	it("releases the reader lock when the stream finishes", async () => {
		const res = makeStreamResponse(['data: {"done": true}\n']);
		fetchMock.mockResolvedValueOnce(res);

		await collect("hi");

		expect(res._reader.releaseLock).toHaveBeenCalledTimes(1);
	});
});

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

describe("streamLetMeCarry errors", () => {
	it("throws when the response is not ok", async () => {
		fetchMock.mockResolvedValueOnce(makeStreamResponse([], { ok: false, status: 500 }));

		await expect(collect("hi")).rejects.toThrow("LetMeCarry request failed (500)");
	});

	it("throws when the response has no body", async () => {
		fetchMock.mockResolvedValueOnce({ ok: true, status: 200, body: null });

		await expect(collect("hi")).rejects.toThrow("LetMeCarry response had no body");
	});
});
