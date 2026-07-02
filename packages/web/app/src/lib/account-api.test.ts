import { apiFetch, fetchWithAuthRetry } from "@slate/shared/api";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	changeEmail,
	confirmEmailChange,
	deleteAccount,
	downloadExport,
	listSessions,
	revokeSession,
	updateProfile,
} from "./account-api";

vi.mock("@slate/shared/api", () => ({
	apiFetch: vi.fn(),
	fetchWithAuthRetry: vi.fn(),
}));

const mockedApiFetch = vi.mocked(apiFetch);
const mockedFetch = vi.mocked(fetchWithAuthRetry);

describe("account-api", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockedApiFetch.mockResolvedValue({} as never);
	});

	it("updateProfile PATCHes /v1/auth/me with the body", async () => {
		await updateProfile({ display_name: "Neo", timezone: "UTC" });
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/me", {
			method: "PATCH",
			body: JSON.stringify({ display_name: "Neo", timezone: "UTC" }),
		});
	});

	it("changeEmail POSTs the new email and password", async () => {
		await changeEmail("new@example.com", "pw"); // pragma: allowlist secret
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/change-email", {
			method: "POST",
			body: JSON.stringify({ new_email: "new@example.com", password: "pw" }),
		});
	});

	it("confirmEmailChange POSTs the token", async () => {
		await confirmEmailChange("tok");
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/confirm-email-change", {
			method: "POST",
			body: JSON.stringify({ token: "tok" }),
		});
	});

	it("listSessions GETs /v1/auth/sessions", async () => {
		await listSessions();
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/sessions");
	});

	it("revokeSession DELETEs the session by id", async () => {
		await revokeSession("abc-123");
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/sessions/abc-123", {
			method: "DELETE",
		});
	});

	it("deleteAccount POSTs the confirmation password", async () => {
		await deleteAccount("pw"); // pragma: allowlist secret
		expect(mockedApiFetch).toHaveBeenCalledWith("/v1/auth/delete-account", {
			method: "POST",
			body: JSON.stringify({ password: "pw" }),
		});
	});

	describe("downloadExport", () => {
		it("saves the export as a blob download on success", async () => {
			mockedFetch.mockResolvedValue({
				ok: true,
				blob: () => Promise.resolve(new Blob(["{}"], { type: "application/json" })),
			} as unknown as Response);
			const createUrl = vi.fn(() => "blob:x");
			const revokeUrl = vi.fn();
			vi.stubGlobal("URL", { createObjectURL: createUrl, revokeObjectURL: revokeUrl });
			const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

			await downloadExport();

			expect(mockedFetch).toHaveBeenCalledWith("/v1/auth/me/export");
			expect(createUrl).toHaveBeenCalled();
			expect(clickSpy).toHaveBeenCalled();
			expect(revokeUrl).toHaveBeenCalledWith("blob:x");
			clickSpy.mockRestore();
			vi.unstubAllGlobals();
		});

		it("throws when the export request fails", async () => {
			mockedFetch.mockResolvedValue({ ok: false, status: 500 } as unknown as Response);
			await expect(downloadExport()).rejects.toThrow(/Export failed/);
		});
	});
});
