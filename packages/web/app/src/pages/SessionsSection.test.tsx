import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useSessions } from "../hooks/useAccount";
import type { SessionInfo } from "../types/auth";
import { SessionsSection } from "./SessionsSection";

vi.mock("../hooks/useAccount", () => ({ useSessions: vi.fn() }));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

const mockSessions = useSessions as Mock;

const sessions: SessionInfo[] = [
	{
		public_id: "s1",
		device_label: "MacBook",
		created_at: "2026-01-01T00:00:00Z",
		last_used_at: "2026-01-02T00:00:00Z",
		expires_at: "2026-02-01T00:00:00Z",
	},
];

function renderSection() {
	return render(
		<MantineProvider>
			<SessionsSection />
		</MantineProvider>,
	);
}

describe("SessionsSection", () => {
	beforeEach(() => vi.clearAllMocks());

	it("shows a loader while loading", () => {
		mockSessions.mockReturnValue({ sessions: [], isLoading: true, revoke: vi.fn() });
		renderSection();
		expect(document.querySelector(".mantine-Loader-root")).toBeTruthy();
	});

	it("shows the empty state", () => {
		mockSessions.mockReturnValue({ sessions: [], isLoading: false, revoke: vi.fn() });
		renderSection();
		expect(screen.getByText("No active sessions.")).toBeInTheDocument();
	});

	it("lists sessions and revokes one", async () => {
		const revoke = vi.fn().mockResolvedValue(undefined);
		mockSessions.mockReturnValue({
			sessions,
			isLoading: false,
			revoke,
			isRevoking: false,
			revokingId: null,
		});
		renderSection();
		expect(screen.getByText("MacBook")).toBeInTheDocument();
		fireEvent.click(screen.getByRole("button", { name: /sign out/i }));
		await waitFor(() => expect(revoke).toHaveBeenCalledWith("s1"));
	});
});
