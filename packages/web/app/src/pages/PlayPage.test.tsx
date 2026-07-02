import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useActivePlaySession } from "../hooks/usePlaySession";
import type { PlaySession } from "../types/play-session";
import { PlayPage } from "./PlayPage";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual("react-router-dom");
	return {
		...actual,
		useNavigate: () => mockNavigate,
	};
});

vi.mock("../hooks/usePlaySession", () => ({
	useActivePlaySession: vi.fn(),
}));

// Force the let_me_carry feature OFF so door-card assertions are deterministic
// regardless of the ambient VITE_ENABLE_LET_ME_CARRY value.
vi.mock("../lib/features", () => ({
	FEATURES: { letMeCarry: false },
}));

function renderPage() {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<PlayPage />
			</MemoryRouter>
		</MantineProvider>,
	);
}

function makePlaySession(overrides: Partial<PlaySession> = {}): PlaySession {
	return {
		publicId: "playSession-1",
		libraryEntry: {
			publicId: "entry-1",
			game: {
				publicId: "game-1",
				slug: "hollow-knight",
				title: "Hollow Knight",
				summary: null,
				coverUrl: null,
				genres: null,
				metadataSource: "igdb",
				createdAt: "2024-01-01T00:00:00Z",
			},
			platform: { id: 1, slug: "pc", label: "PC", family: "pc" },
			status: "playing",
			playSessionNextAction: null,
			notes: null,
			createdAt: "2024-06-01T00:00:00Z",
			updatedAt: "2024-06-02T00:00:00Z",
		},
		playSessionType: "regular",
		recapText: "Your next adventure awaits",
		wrapUpText: null,
		extractedState: null,
		endedVia: null,
		startedAt: "2024-06-02T10:00:00Z",
		endedAt: null,
		createdAt: "2024-06-02T10:00:00Z",
		updatedAt: "2024-06-02T10:00:00Z",
		lastSessionContext: null,
		...overrides,
	};
}

beforeEach(() => {
	vi.clearAllMocks();
	(useActivePlaySession as Mock).mockReturnValue({ data: null });
});

describe("PlayPage", () => {
	it("renders the Play title", () => {
		renderPage();
		expect(screen.getByText("Play")).toBeInTheDocument();
	});

	it("renders the two non-let_me_carry door cards in order", () => {
		renderPage();
		expect(screen.getByText("What's the move?")).toBeInTheDocument();
		expect(screen.getByText("I'll choose")).toBeInTheDocument();
		// LetMeCarry feature is off by default, so the Ask door is hidden.
		expect(screen.queryByText("Ask")).not.toBeInTheDocument();
	});

	it("navigates to /play/pick from the 'What's the move?' door", () => {
		renderPage();
		fireEvent.click(screen.getByText("What's the move?"));
		expect(mockNavigate).toHaveBeenCalledWith("/play/pick");
	});

	it("navigates to /library from the 'I'll choose' door", () => {
		renderPage();
		fireEvent.click(screen.getByText("I'll choose"));
		expect(mockNavigate).toHaveBeenCalledWith("/library");
	});

	it("disables the start doors and does not navigate when a playSession is active", () => {
		(useActivePlaySession as Mock).mockReturnValue({ data: makePlaySession() });
		renderPage();

		fireEvent.click(screen.getByText("What's the move?"));
		fireEvent.click(screen.getByText("I'll choose"));

		expect(mockNavigate).not.toHaveBeenCalled();
	});
});
