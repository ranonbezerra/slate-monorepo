import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAuthContext } from "../contexts/AuthContext";
import { useUpdateProfile } from "../hooks/useAccount";
import { ProfileSection } from "./ProfileSection";

vi.mock("../contexts/AuthContext", () => ({ useAuthContext: vi.fn() }));
vi.mock("../hooks/useAccount", () => ({ useUpdateProfile: vi.fn() }));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

const mockAuth = useAuthContext as Mock;
const mockUpdate = useUpdateProfile as Mock;

const user = {
	display_name: "Trinity",
	locale: "en",
	timezone: "UTC",
	email: "t@example.com",
};

function renderSection() {
	return render(
		<MantineProvider>
			<ProfileSection />
		</MantineProvider>,
	);
}

describe("ProfileSection", () => {
	let updateProfile: Mock;
	beforeEach(() => {
		vi.clearAllMocks();
		updateProfile = vi.fn().mockResolvedValue(undefined);
		mockAuth.mockReturnValue({ user });
		mockUpdate.mockReturnValue({ updateProfile, isPending: false });
	});

	it("prefills the display name and disables save until dirty", () => {
		renderSection();
		expect(screen.getByDisplayValue("Trinity")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: /save changes/i })).toBeDisabled();
	});

	it("submits the edited profile", async () => {
		renderSection();
		fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "Neo" } });
		const form = screen.getByRole("button", { name: /save changes/i }).closest("form");
		if (!form) throw new Error("no form");
		fireEvent.submit(form);

		await waitFor(() =>
			expect(updateProfile).toHaveBeenCalledWith(
				expect.objectContaining({ display_name: "Neo", locale: "en", timezone: "UTC" }),
			),
		);
		expect(notifications.show).toHaveBeenCalledWith(expect.objectContaining({ color: "green" }));
	});

	it("shows an error notification when the update fails", async () => {
		updateProfile.mockRejectedValueOnce(new Error("nope"));
		renderSection();
		fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "Neo" } });
		const form = screen.getByRole("button", { name: /save changes/i }).closest("form");
		if (!form) throw new Error("no form");
		fireEvent.submit(form);

		await waitFor(() =>
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Couldn't update profile", color: "red" }),
			),
		);
	});
});
