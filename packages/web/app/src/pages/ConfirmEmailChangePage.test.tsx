import { MantineProvider } from "@mantine/core";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { confirmEmailChange } from "../lib/account-api";
import { ConfirmEmailChangePage } from "./ConfirmEmailChangePage";

vi.mock("../lib/account-api", () => ({ confirmEmailChange: vi.fn() }));

function renderAt(entry: string) {
	return render(
		<MantineProvider>
			<MemoryRouter initialEntries={[entry]}>
				<ConfirmEmailChangePage />
			</MemoryRouter>
		</MantineProvider>,
	);
}

describe("ConfirmEmailChangePage", () => {
	beforeEach(() => vi.clearAllMocks());

	it("shows the missing-token state when no token is present", () => {
		renderAt("/confirm-email-change");
		expect(screen.getByText("Missing token")).toBeInTheDocument();
		expect(confirmEmailChange).not.toHaveBeenCalled();
	});

	it("confirms the change on a valid token", async () => {
		vi.mocked(confirmEmailChange).mockResolvedValueOnce({ message: "ok" });
		renderAt("/confirm-email-change?token=good");
		await waitFor(() => expect(screen.getByText("Email updated")).toBeInTheDocument());
		expect(confirmEmailChange).toHaveBeenCalledWith("good");
	});

	it("shows an error on an invalid token", async () => {
		vi.mocked(confirmEmailChange).mockRejectedValueOnce(new Error("expired"));
		renderAt("/confirm-email-change?token=bad");
		await waitFor(() => expect(screen.getByText("Confirmation failed")).toBeInTheDocument());
	});
});
