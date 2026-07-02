import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AccountPage } from "./AccountPage";

vi.mock("./ChangePasswordPage", () => ({
	ChangePasswordPage: () => <div data-testid="change-password" />,
}));
vi.mock("./MfaSection", () => ({ MfaSection: () => <div data-testid="mfa-section" /> }));
vi.mock("./ProfileSection", () => ({
	ProfileSection: () => <div data-testid="profile-section" />,
}));
vi.mock("./EmailSection", () => ({ EmailSection: () => <div data-testid="email-section" /> }));
vi.mock("./SessionsSection", () => ({
	SessionsSection: () => <div data-testid="sessions-section" />,
}));
vi.mock("./DataPrivacySection", () => ({
	DataPrivacySection: () => <div data-testid="data-section" />,
}));
vi.mock("./SteamSyncSection", () => ({
	SteamSyncSection: () => <div data-testid="steam-section" />,
}));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

// Mutable feature flag + search params so individual tests can toggle them.
// Wrapped in vi.hoisted so the mock factories (which run before top-level code)
// can safely reference them.
const h = vi.hoisted(() => ({
	features: { letMeCarry: false, steamImport: false },
	setSearchParams: vi.fn(),
	searchParams: new URLSearchParams(),
}));
vi.mock("../lib/features", () => ({ FEATURES: h.features }));
vi.mock("react-router-dom", () => ({
	useSearchParams: () => [h.searchParams, h.setSearchParams] as const,
}));

function renderPage() {
	return render(
		<MantineProvider>
			<AccountPage />
		</MantineProvider>,
	);
}

describe("AccountPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		h.features.steamImport = false;
		h.searchParams = new URLSearchParams();
	});
	afterEach(() => {
		vi.clearAllMocks();
	});

	it("shows the Settings heading and the Profile tab by default", () => {
		renderPage();
		expect(screen.getByRole("heading", { name: /settings/i })).toBeInTheDocument();
		expect(screen.getByTestId("profile-section")).toBeInTheDocument();
		expect(screen.getByTestId("email-section")).toBeInTheDocument();
	});

	it("switches to the Security tab", () => {
		renderPage();
		fireEvent.click(screen.getByRole("tab", { name: /security/i }));
		expect(screen.getByTestId("change-password")).toBeInTheDocument();
		expect(screen.getByTestId("mfa-section")).toBeInTheDocument();
	});

	it("switches to the Sessions tab", () => {
		renderPage();
		fireEvent.click(screen.getByRole("tab", { name: /sessions/i }));
		expect(screen.getByTestId("sessions-section")).toBeInTheDocument();
	});

	it("switches to the Data & privacy tab", () => {
		renderPage();
		fireEvent.click(screen.getByRole("tab", { name: /data & privacy/i }));
		expect(screen.getByTestId("data-section")).toBeInTheDocument();
	});

	it("hides the Connections tab when the steam flag is off", () => {
		renderPage();
		expect(screen.queryByRole("tab", { name: /connections/i })).not.toBeInTheDocument();
	});

	it("shows the Connections tab with Steam sync when the flag is on", () => {
		h.features.steamImport = true;
		renderPage();
		fireEvent.click(screen.getByRole("tab", { name: /connections/i }));
		expect(screen.getByTestId("steam-section")).toBeInTheDocument();
	});

	it("toasts green and clears the param on ?steam=connected", async () => {
		h.searchParams = new URLSearchParams("steam=connected");
		renderPage();
		await waitFor(() =>
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Steam connected", color: "green" }),
			),
		);
		expect(h.setSearchParams).toHaveBeenCalledWith({}, { replace: true });
	});

	it("toasts red on ?steam=error", async () => {
		h.searchParams = new URLSearchParams("steam=error");
		renderPage();
		await waitFor(() =>
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Couldn't connect Steam", color: "red" }),
			),
		);
		expect(h.setSearchParams).toHaveBeenCalledWith({}, { replace: true });
	});

	it("does nothing when there is no steam param", () => {
		renderPage();
		expect(notifications.show).not.toHaveBeenCalled();
		expect(h.setSearchParams).not.toHaveBeenCalled();
	});
});
