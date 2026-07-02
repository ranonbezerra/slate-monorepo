import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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

function renderPage() {
	return render(
		<MantineProvider>
			<AccountPage />
		</MantineProvider>,
	);
}

describe("AccountPage", () => {
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
});
