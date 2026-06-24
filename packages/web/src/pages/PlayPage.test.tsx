import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useActiveMission } from "../hooks/useMission";
import type { Mission } from "../types/mission";
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

vi.mock("../hooks/useMission", () => ({
	useActiveMission: vi.fn(),
}));

// Force the concierge feature OFF so door-card assertions are deterministic
// regardless of the ambient VITE_ENABLE_CONCIERGE value.
vi.mock("../lib/features", () => ({
	FEATURES: { backlogConcierge: false },
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

function makeMission(overrides: Partial<Mission> = {}): Mission {
	return {
		publicId: "mission-1",
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
			missionNextAction: null,
			notes: null,
			createdAt: "2024-06-01T00:00:00Z",
			updatedAt: "2024-06-02T00:00:00Z",
		},
		missionType: "regular",
		briefingText: "Your next adventure awaits",
		debriefText: null,
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
	(useActiveMission as Mock).mockReturnValue({ data: null });
});

describe("PlayPage", () => {
	it("renders the Play title", () => {
		renderPage();
		expect(screen.getByText("Play")).toBeInTheDocument();
	});

	it("shows an empty hint when there is no active mission", () => {
		renderPage();
		expect(screen.getByText(/No active mission/)).toBeInTheDocument();
	});

	it("renders the two non-concierge door cards in order", () => {
		renderPage();
		expect(screen.getByText("What's the move?")).toBeInTheDocument();
		expect(screen.getByText("I'll choose")).toBeInTheDocument();
		// Concierge feature is off by default, so the Ask door is hidden.
		expect(screen.queryByText("Ask")).not.toBeInTheDocument();
	});

	it("navigates to /play/loadout from the 'What's the move?' door", () => {
		renderPage();
		fireEvent.click(screen.getByText("What's the move?"));
		expect(mockNavigate).toHaveBeenCalledWith("/play/loadout");
	});

	it("navigates to /library from the 'I'll choose' door", () => {
		renderPage();
		fireEvent.click(screen.getByText("I'll choose"));
		expect(mockNavigate).toHaveBeenCalledWith("/library");
	});

	it("shows the active mission card with the game title and briefing", () => {
		(useActiveMission as Mock).mockReturnValue({ data: makeMission() });
		renderPage();
		expect(screen.getByText("Mission active")).toBeInTheDocument();
		expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
		expect(screen.getByText("Your next adventure awaits")).toBeInTheDocument();
	});

	it("navigates to /play/missions from the Resume button", () => {
		(useActiveMission as Mock).mockReturnValue({ data: makeMission() });
		renderPage();
		fireEvent.click(screen.getByRole("button", { name: /resume/i }));
		expect(mockNavigate).toHaveBeenCalledWith("/play/missions");
	});

	it("navigates to /play/missions from the End / Debrief button", () => {
		(useActiveMission as Mock).mockReturnValue({ data: makeMission() });
		renderPage();
		fireEvent.click(screen.getByRole("button", { name: /end \/ debrief/i }));
		expect(mockNavigate).toHaveBeenCalledWith("/play/missions");
	});
});
