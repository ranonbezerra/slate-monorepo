import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { createElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	changeEmail,
	deleteAccount,
	listSessions,
	revokeSession,
	updateProfile,
} from "../lib/account-api";
import type { SessionInfo, User } from "../types/auth";
import { useChangeEmail, useDeleteAccount, useSessions, useUpdateProfile } from "./useAccount";

vi.mock("../lib/account-api", () => ({
	updateProfile: vi.fn(),
	changeEmail: vi.fn(),
	listSessions: vi.fn(),
	revokeSession: vi.fn(),
	deleteAccount: vi.fn(),
}));

function makeWrapper() {
	const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
	const wrapper = ({ children }: { children: ReactNode }) =>
		createElement(QueryClientProvider, { client: qc }, children);
	return { qc, wrapper };
}

const fakeUser: User = {
	public_id: "u1",
	email: "a@b.com",
	display_name: "A",
	avatar_url: null,
	email_verified: true,
	emailVerified: true,
	locale: "en",
	timezone: "UTC",
	created_at: "2026-01-01T00:00:00Z",
};

describe("useAccount hooks", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("useUpdateProfile writes the fresh user into the /me cache", async () => {
		vi.mocked(updateProfile).mockResolvedValueOnce(fakeUser);
		const { qc, wrapper } = makeWrapper();
		const { result } = renderHook(() => useUpdateProfile(), { wrapper });

		await act(async () => {
			await result.current.updateProfile({ display_name: "A" });
		});

		expect(updateProfile).toHaveBeenCalledWith({ display_name: "A" });
		expect(qc.getQueryData(["auth", "me"])).toMatchObject({
			email: "a@b.com",
			emailVerified: true,
		});
	});

	it("useChangeEmail forwards the new email and password", async () => {
		vi.mocked(changeEmail).mockResolvedValueOnce({ message: "ok" });
		const { wrapper } = makeWrapper();
		const { result } = renderHook(() => useChangeEmail(), { wrapper });

		await act(async () => {
			await result.current.changeEmail("new@b.com", "pw"); // pragma: allowlist secret
		});

		expect(changeEmail).toHaveBeenCalledWith("new@b.com", "pw");
	});

	it("useSessions lists sessions and revokes one", async () => {
		const sessions: SessionInfo[] = [
			{
				public_id: "s1",
				device_label: "Laptop",
				created_at: "2026-01-01T00:00:00Z",
				last_used_at: null,
				expires_at: "2026-02-01T00:00:00Z",
			},
		];
		vi.mocked(listSessions).mockResolvedValue(sessions);
		vi.mocked(revokeSession).mockResolvedValueOnce(undefined);
		const { wrapper } = makeWrapper();
		const { result } = renderHook(() => useSessions(), { wrapper });

		await waitFor(() => expect(result.current.sessions).toHaveLength(1));

		await act(async () => {
			await result.current.revoke("s1");
		});
		expect(revokeSession).toHaveBeenCalledWith("s1");
	});

	it("useDeleteAccount posts the password", async () => {
		vi.mocked(deleteAccount).mockResolvedValueOnce({ message: "gone" });
		const { wrapper } = makeWrapper();
		const { result } = renderHook(() => useDeleteAccount(), { wrapper });

		await act(async () => {
			await result.current.deleteAccount("pw"); // pragma: allowlist secret
		});
		expect(deleteAccount).toHaveBeenCalledWith("pw");
	});
});
