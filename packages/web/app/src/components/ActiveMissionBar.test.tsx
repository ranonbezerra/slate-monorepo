import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useActivePlaySession } from "../hooks/usePlaySession";
import { FEATURES } from "../lib/features";
import type { PlaySession } from "../types/play-session";
import { ActiveMissionBar } from "./ActiveMissionBar";

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

// let_me_carry is off by default; individual tests flip it on via the mutable
// mock object below.
vi.mock("../lib/features", () => ({
	FEATURES: { letMeCarry: false },
}));

// The recap/wrapUp modals pull in their own data hooks; stub them so this suite
// stays focused on the bar and needs no QueryClient provider.
vi.mock("../pages/PlaySessionRecapModal", () => ({
	PlaySessionRecapModal: ({ mode }: { mode: string }) => (
		<div data-testid="recap-modal">{mode}</div>
	),
}));
vi.mock("../pages/PlaySessionWrapUpModal", () => ({
	PlaySessionWrapUpModal: ({ playSession }: { playSession: unknown }) =>
		playSession ? <div data-testid="wrapUp-modal" /> : null,
}));

function renderBar() {
	return render(
		<MantineProvider>
			<MemoryRouter>
				<ActiveMissionBar />
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
	(FEATURES as { letMeCarry: boolean }).letMeCarry = false;
	(useActivePlaySession as Mock).mockReturnValue({ data: null });
});

describe("ActiveMissionBar", () => {
	it("renders nothing when there is no active session", () => {
		renderBar();
		expect(screen.queryByText("Session active")).not.toBeInTheDocument();
		expect(screen.queryByRole("button", { name: /wrap up/i })).not.toBeInTheDocument();
	});

	it("renders the bar with the game title and Wrap up button when a session is active", () => {
		(useActivePlaySession as Mock).mockReturnValue({ data: makePlaySession() });
		renderBar();
		expect(screen.getByText("Session active")).toBeInTheDocument();
		expect(screen.getByText("Hollow Knight")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /wrap up/i })).toBeInTheDocument();
	});

	it("shows the Recap button only when the active session has recap text", () => {
		(useActivePlaySession as Mock).mockReturnValue({
			data: makePlaySession({ recapText: null }),
		});
		const { unmount } = renderBar();
		expect(screen.queryByRole("button", { name: /recap/i })).not.toBeInTheDocument();
		unmount();

		(useActivePlaySession as Mock).mockReturnValue({ data: makePlaySession() });
		renderBar();
		expect(screen.getByRole("button", { name: /recap/i })).toBeInTheDocument();
	});

	it("opens the recap modal in view mode from the Recap button", () => {
		(useActivePlaySession as Mock).mockReturnValue({ data: makePlaySession() });
		renderBar();
		expect(screen.queryByTestId("recap-modal")).not.toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: /recap/i }));
		const modal = screen.getByTestId("recap-modal");
		expect(modal).toHaveTextContent("view");
		expect(mockNavigate).not.toHaveBeenCalled();
	});

	it("opens the wrapUp modal from the Wrap up button", () => {
		(useActivePlaySession as Mock).mockReturnValue({ data: makePlaySession() });
		renderBar();
		expect(screen.queryByTestId("wrapUp-modal")).not.toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: /wrap up/i }));
		expect(screen.getByTestId("wrapUp-modal")).toBeInTheDocument();
		expect(mockNavigate).not.toHaveBeenCalled();
	});

	it("hides the Carry me! button when the let_me_carry feature is off", () => {
		(useActivePlaySession as Mock).mockReturnValue({ data: makePlaySession() });
		renderBar();
		expect(screen.queryByRole("button", { name: /carry me/i })).not.toBeInTheDocument();
	});

	it("shows Carry me! when the feature is on and navigates to /play/let-me-carry", () => {
		(FEATURES as { letMeCarry: boolean }).letMeCarry = true;
		(useActivePlaySession as Mock).mockReturnValue({ data: makePlaySession() });
		renderBar();
		const carry = screen.getByRole("button", { name: /carry me/i });
		expect(carry).toBeInTheDocument();
		fireEvent.click(carry);
		expect(mockNavigate).toHaveBeenCalledWith("/play/let-me-carry");
	});
});
