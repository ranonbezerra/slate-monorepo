import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAuthContext } from "../contexts/AuthContext";
import { useChangeEmail } from "../hooks/useAccount";
import { EmailSection } from "./EmailSection";

vi.mock("../contexts/AuthContext", () => ({ useAuthContext: vi.fn() }));
vi.mock("../hooks/useAccount", () => ({ useChangeEmail: vi.fn() }));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

const mockAuth = useAuthContext as Mock;
const mockChange = useChangeEmail as Mock;

function renderSection() {
	return render(
		<MantineProvider>
			<EmailSection />
		</MantineProvider>,
	);
}

describe("EmailSection", () => {
	let changeEmail: Mock;
	beforeEach(() => {
		vi.clearAllMocks();
		changeEmail = vi.fn().mockResolvedValue({ message: "ok" });
		mockAuth.mockReturnValue({ user: { email: "old@example.com" } });
		mockChange.mockReturnValue({ changeEmail, isPending: false });
	});

	it("shows the current email", () => {
		renderSection();
		expect(screen.getByText("old@example.com")).toBeInTheDocument();
	});

	it("requests a change with the new email and password", async () => {
		renderSection();
		fireEvent.change(screen.getByLabelText("New email"), {
			target: { value: "new@example.com" },
		});
		fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "pw" } });
		const form = screen.getByRole("button", { name: /send confirmation link/i }).closest("form");
		if (!form) throw new Error("no form");
		fireEvent.submit(form);

		await waitFor(() => expect(changeEmail).toHaveBeenCalledWith("new@example.com", "pw"));
		expect(notifications.show).toHaveBeenCalledWith(expect.objectContaining({ color: "blue" }));
	});

	it("surfaces an error notification on failure", async () => {
		changeEmail.mockRejectedValueOnce(new Error("in use"));
		renderSection();
		fireEvent.change(screen.getByLabelText("New email"), {
			target: { value: "new@example.com" },
		});
		fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "pw" } });
		const form = screen.getByRole("button", { name: /send confirmation link/i }).closest("form");
		if (!form) throw new Error("no form");
		fireEvent.submit(form);

		await waitFor(() =>
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Couldn't change email", color: "red" }),
			),
		);
	});
});
