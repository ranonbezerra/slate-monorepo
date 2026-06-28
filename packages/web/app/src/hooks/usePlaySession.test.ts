import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createWrapper } from "../test/wrapper";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@dl/shared/api", () => ({
	BASE_URL: "http://localhost:8100",
	apiFetch: vi.fn(() => Promise.resolve(null)),
	getAccessToken: vi.fn(() => null),
	getRefreshToken: vi.fn(() => null),
	saveTokens: vi.fn(),
	clearTokens: vi.fn(),
}));

const mockLibraryEntry = {
	publicId: "entry-1",
	game: {
		publicId: "game-1",
		slug: "elden-ring",
		title: "Elden Ring",
		metadataSource: "igdb",
		createdAt: "2024-01-01T00:00:00Z",
	},
	platform: { id: 1, slug: "pc", label: "PC", family: "computer" },
	status: "playing" as const,
	createdAt: "2024-01-01T00:00:00Z",
	updatedAt: "2024-06-01T00:00:00Z",
};

const mockPlaySession = {
	publicId: "playSession-1",
	libraryEntry: mockLibraryEntry,
	playSessionType: "regular" as const,
	briefingText: "Continue from Stormveil Castle.",
	debriefText: null,
	extractedState: null,
	endedVia: null,
	startedAt: "2024-06-15T18:00:00Z",
	endedAt: null,
	createdAt: "2024-06-15T18:00:00Z",
	updatedAt: "2024-06-15T18:00:00Z",
	lastSessionContext: {
		location: "Stormveil Castle",
		nextAction: "Defeat Godrick",
		level: "45",
		currentQuest: "Main story",
	},
};

const mockPlaySessionListResponse = {
	items: [
		{
			publicId: "playSession-1",
			libraryEntry: mockLibraryEntry,
			playSessionType: "regular" as const,
			endedVia: null,
			startedAt: "2024-06-15T18:00:00Z",
			endedAt: null,
		},
	],
	total: 1,
};

const mockBriefingPreview = {
	libraryEntry: mockLibraryEntry,
	briefingText: "You are about to enter Stormveil Castle.",
	lastSessionContext: {
		location: "Limgrave",
		nextAction: "Head to Stormveil",
		level: "40",
		currentQuest: null,
	},
};

vi.mock("../lib/play-session-api", () => ({
	listPlaySessions: vi.fn(() => Promise.resolve(mockPlaySessionListResponse)),
	getPlaySession: vi.fn(() => Promise.resolve(mockPlaySession)),
	getActivePlaySession: vi.fn(() => Promise.resolve(mockPlaySession)),
	previewBriefing: vi.fn(() => Promise.resolve(mockBriefingPreview)),
	startPlaySession: vi.fn(() => Promise.resolve(mockPlaySession)),
	submitDebrief: vi.fn(() =>
		Promise.resolve({ ...mockPlaySession, debriefText: "Defeated Godrick." }),
	),
	endPlaySession: vi.fn(() =>
		Promise.resolve({
			...mockPlaySession,
			endedVia: "paused_app",
			endedAt: "2024-06-15T20:00:00Z",
		}),
	),
	regenerateBriefing: vi.fn(() =>
		Promise.resolve({ ...mockPlaySession, briefingText: "New briefing text." }),
	),
	submitRetroactiveDebrief: vi.fn(() => Promise.resolve(mockBriefingPreview)),
}));

import {
	endPlaySession,
	getActivePlaySession,
	getPlaySession,
	listPlaySessions,
	previewBriefing,
	regenerateBriefing,
	startPlaySession,
	submitDebrief,
	submitRetroactiveDebrief,
} from "../lib/play-session-api";
import {
	useActivePlaySession,
	useEndPlaySession,
	usePlaySession,
	usePlaySessions,
	usePreviewBriefing,
	useRegenerateBriefing,
	useRetroactiveDebrief,
	useStartPlaySession,
	useSubmitDebrief,
} from "./usePlaySession";

beforeEach(() => {
	vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

describe("usePlaySessions", () => {
	it("returns playSession list without params", async () => {
		const { result } = renderHook(() => usePlaySessions(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(listPlaySessions).toHaveBeenCalledWith(undefined);
		expect(result.current.data).toEqual(mockPlaySessionListResponse);
	});

	it("passes pagination params to listPlaySessions", async () => {
		const params = { limit: 10, offset: 5 };
		const { result } = renderHook(() => usePlaySessions(params), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(listPlaySessions).toHaveBeenCalledWith(params);
	});
});

describe("usePlaySession", () => {
	it("is disabled when publicId is empty", () => {
		const { result } = renderHook(() => usePlaySession(""), {
			wrapper: createWrapper(),
		});

		expect(result.current.fetchStatus).toBe("idle");
		expect(getPlaySession).not.toHaveBeenCalled();
	});

	it("fetches a single playSession when publicId is truthy", async () => {
		const { result } = renderHook(() => usePlaySession("playSession-1"), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(getPlaySession).toHaveBeenCalledWith("playSession-1");
		expect(result.current.data).toEqual(mockPlaySession);
	});
});

describe("useActivePlaySession", () => {
	it("returns the active playSession", async () => {
		const { result } = renderHook(() => useActivePlaySession(), {
			wrapper: createWrapper(),
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));

		expect(getActivePlaySession).toHaveBeenCalledOnce();
		expect(result.current.data).toEqual(mockPlaySession);
	});
});

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

describe("usePreviewBriefing", () => {
	it("calls previewBriefing with libraryEntryPublicId", async () => {
		const { result } = renderHook(() => usePreviewBriefing(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ libraryEntryPublicId: "entry-1" });

		expect(previewBriefing).toHaveBeenCalledWith("entry-1", undefined, undefined, undefined);
	});

	it("calls previewBriefing with optional positionOverride", async () => {
		const { result } = renderHook(() => usePreviewBriefing(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			libraryEntryPublicId: "entry-1",
			positionOverride: "Chapter 3",
		});

		expect(previewBriefing).toHaveBeenCalledWith("entry-1", "Chapter 3", undefined, undefined);
	});
});

describe("useStartPlaySession", () => {
	it("calls startPlaySession with libraryEntryPublicId", async () => {
		const { result } = renderHook(() => useStartPlaySession(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ libraryEntryPublicId: "entry-1" });

		expect(startPlaySession).toHaveBeenCalledWith("entry-1", undefined, undefined);
	});

	it("calls startPlaySession with optional briefingText", async () => {
		const { result } = renderHook(() => useStartPlaySession(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			libraryEntryPublicId: "entry-1",
			briefingText: "Custom briefing",
		});

		expect(startPlaySession).toHaveBeenCalledWith("entry-1", "Custom briefing", undefined);
	});

	it("passes skipBriefing through to start with no briefing", async () => {
		const { result } = renderHook(() => useStartPlaySession(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ libraryEntryPublicId: "entry-1", skipBriefing: true });

		expect(startPlaySession).toHaveBeenCalledWith("entry-1", undefined, true);
	});
});

describe("useSubmitDebrief", () => {
	it("calls submitDebrief with publicId and debriefText", async () => {
		const { result } = renderHook(() => useSubmitDebrief(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			publicId: "playSession-1",
			debriefText: "Defeated Godrick. Heading to Liurnia.",
		});

		expect(submitDebrief).toHaveBeenCalledWith(
			"playSession-1",
			"Defeated Godrick. Heading to Liurnia.",
		);
	});
});

describe("useEndPlaySession", () => {
	it("calls endPlaySession with publicId and default endedVia", async () => {
		const { result } = renderHook(() => useEndPlaySession(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ publicId: "playSession-1" });

		expect(endPlaySession).toHaveBeenCalledWith("playSession-1", undefined);
	});

	it("calls endPlaySession with explicit endedVia", async () => {
		const { result } = renderHook(() => useEndPlaySession(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ publicId: "playSession-1", endedVia: "paused_app" });

		expect(endPlaySession).toHaveBeenCalledWith("playSession-1", "paused_app");
	});
});

describe("useRegenerateBriefing", () => {
	it("calls regenerateBriefing with publicId", async () => {
		const { result } = renderHook(() => useRegenerateBriefing(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({ publicId: "playSession-1" });

		expect(regenerateBriefing).toHaveBeenCalledWith("playSession-1", undefined);
	});

	it("calls regenerateBriefing with currentPosition", async () => {
		const { result } = renderHook(() => useRegenerateBriefing(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			publicId: "playSession-1",
			currentPosition: "Liurnia of the Lakes",
		});

		expect(regenerateBriefing).toHaveBeenCalledWith("playSession-1", "Liurnia of the Lakes");
	});
});

describe("useRetroactiveDebrief", () => {
	it("calls submitRetroactiveDebrief with libraryEntryPublicId and debriefText", async () => {
		const { result } = renderHook(() => useRetroactiveDebrief(), {
			wrapper: createWrapper(),
		});

		await result.current.mutateAsync({
			libraryEntryPublicId: "entry-1",
			debriefText: "Played for two hours, cleared a dungeon.",
		});

		expect(submitRetroactiveDebrief).toHaveBeenCalledWith(
			"entry-1",
			"Played for two hours, cleared a dungeon.",
		);
	});
});
