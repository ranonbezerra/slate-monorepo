import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { ApiError } from "@slate/shared/api";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { importSteamLibrary, steamStart } from "../lib/steam-api";
import { SteamSyncSection } from "./SteamSyncSection";

vi.mock("../lib/steam-api", () => ({
	steamStart: vi.fn(),
	importSteamLibrary: vi.fn(),
}));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

function renderSection() {
	const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
	return render(
		<QueryClientProvider client={client}>
			<MantineProvider>
				<SteamSyncSection />
			</MantineProvider>
		</QueryClientProvider>,
	);
}

describe("SteamSyncSection", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		// window.location.href is a plain assignable string in jsdom, but replace
		// it defensively so the navigate doesn't blow up the test environment.
		Object.defineProperty(window, "location", {
			configurable: true,
			value: { href: "" },
		});
	});

	it("starts the Steam flow and navigates to the returned URL", async () => {
		vi.mocked(steamStart).mockResolvedValueOnce({
			redirect_url: "https://steamcommunity.com/openid/login?x=1",
		});
		renderSection();
		fireEvent.click(screen.getByRole("button", { name: /connect steam/i }));

		await waitFor(() => expect(steamStart).toHaveBeenCalledOnce());
		expect(window.location.href).toBe("https://steamcommunity.com/openid/login?x=1");
	});

	it("notifies red when starting the Steam flow fails", async () => {
		vi.mocked(steamStart).mockRejectedValueOnce(new Error("boom"));
		renderSection();
		fireEvent.click(screen.getByRole("button", { name: /connect steam/i }));

		await waitFor(() =>
			expect(notifications.show).toHaveBeenCalledWith(expect.objectContaining({ color: "red" })),
		);
	});

	it("imports the library and shows a green summary", async () => {
		vi.mocked(importSteamLibrary).mockResolvedValueOnce({
			imported: 12,
			already_owned: 3,
			unmatched: 1,
			private_or_empty: false,
		});
		renderSection();
		fireEvent.click(screen.getByRole("button", { name: /import my steam library/i }));

		await waitFor(() =>
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					color: "green",
					message: expect.stringContaining("Imported 12 games"),
				}),
			),
		);
	});

	it("shows the yellow hint when the profile is private or empty", async () => {
		vi.mocked(importSteamLibrary).mockResolvedValueOnce({
			imported: 0,
			already_owned: 0,
			unmatched: 0,
			private_or_empty: true,
		});
		renderSection();
		fireEvent.click(screen.getByRole("button", { name: /import my steam library/i }));

		await waitFor(() =>
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					color: "yellow",
					message: expect.stringContaining("public"),
				}),
			),
		);
	});

	it("hints to connect first on a 409 not-connected error", async () => {
		vi.mocked(importSteamLibrary).mockRejectedValueOnce(
			new ApiError(409, "Steam is not connected"),
		);
		renderSection();
		fireEvent.click(screen.getByRole("button", { name: /import my steam library/i }));

		await waitFor(() =>
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					color: "yellow",
					title: expect.stringMatching(/isn't connected/i),
				}),
			),
		);
	});

	it("notifies red on a generic import failure", async () => {
		vi.mocked(importSteamLibrary).mockRejectedValueOnce(new Error("nope"));
		renderSection();
		fireEvent.click(screen.getByRole("button", { name: /import my steam library/i }));

		await waitFor(() =>
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({
					color: "red",
					title: expect.stringMatching(/couldn't import/i),
				}),
			),
		);
	});
});
