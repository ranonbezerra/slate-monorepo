import { MantineProvider } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, type Mock, vi } from "vitest";
import { useAuthContext } from "../contexts/AuthContext";
import { useDeleteAccount } from "../hooks/useAccount";
import { downloadExport } from "../lib/account-api";
import { DataPrivacySection } from "./DataPrivacySection";

const navigate = vi.fn();
vi.mock("react-router-dom", () => ({ useNavigate: () => navigate }));
vi.mock("../contexts/AuthContext", () => ({ useAuthContext: vi.fn() }));
vi.mock("../hooks/useAccount", () => ({ useDeleteAccount: vi.fn() }));
vi.mock("../lib/account-api", () => ({ downloadExport: vi.fn() }));
vi.mock("@mantine/notifications", () => ({ notifications: { show: vi.fn() } }));

const mockAuth = useAuthContext as Mock;
const mockDelete = useDeleteAccount as Mock;

function renderSection() {
	return render(
		<MantineProvider>
			<DataPrivacySection />
		</MantineProvider>,
	);
}

describe("DataPrivacySection", () => {
	let logout: Mock;
	let deleteAccount: Mock;
	beforeEach(() => {
		vi.clearAllMocks();
		logout = vi.fn().mockResolvedValue(undefined);
		deleteAccount = vi.fn().mockResolvedValue({ message: "gone" });
		mockAuth.mockReturnValue({ logout });
		mockDelete.mockReturnValue({ deleteAccount, isPending: false });
	});

	it("exports data on click", async () => {
		vi.mocked(downloadExport).mockResolvedValueOnce(undefined);
		renderSection();
		fireEvent.click(screen.getByRole("button", { name: /export my data/i }));
		await waitFor(() => expect(downloadExport).toHaveBeenCalledOnce());
	});

	it("notifies when export fails", async () => {
		vi.mocked(downloadExport).mockRejectedValueOnce(new Error("boom"));
		renderSection();
		fireEvent.click(screen.getByRole("button", { name: /export my data/i }));
		await waitFor(() =>
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Export failed", color: "red" }),
			),
		);
	});

	it("deletes the account after confirming with a password", async () => {
		renderSection();
		fireEvent.click(screen.getByRole("button", { name: /delete my account/i }));
		fireEvent.change(screen.getByLabelText("Confirm your password"), {
			target: { value: "pw" },
		});
		fireEvent.click(screen.getByRole("button", { name: /permanently delete/i }));

		await waitFor(() => expect(deleteAccount).toHaveBeenCalledWith("pw"));
		expect(logout).toHaveBeenCalled();
		expect(navigate).toHaveBeenCalledWith("/login", { replace: true });
	});

	it("can cancel the delete confirmation", () => {
		renderSection();
		fireEvent.click(screen.getByRole("button", { name: /delete my account/i }));
		fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
		expect(screen.queryByLabelText("Confirm your password")).not.toBeInTheDocument();
	});
});
