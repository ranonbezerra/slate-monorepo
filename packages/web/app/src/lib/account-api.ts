import { apiFetch, fetchWithAuthRetry } from "@slate/shared/api";
import type { MessageResponse, SessionInfo, UpdateProfileInput, User } from "../types/auth";

// ---------------------------------------------------------------------------
// Account settings API — profile, email change, sessions, export, erasure.
//
// All routes are authenticated; `apiFetch` attaches the in-memory access token
// and transparently refreshes on 401. Destructive/sensitive routes re-auth with
// the account password (verified server-side).
// ---------------------------------------------------------------------------

/** PATCH /v1/auth/me — partial profile update; returns the fresh user. */
export function updateProfile(body: UpdateProfileInput): Promise<User> {
	return apiFetch<User>("/v1/auth/me", {
		method: "PATCH",
		body: JSON.stringify(body),
	});
}

/** POST /v1/auth/change-email — re-auth, then email a confirm link to the new address. */
export function changeEmail(newEmail: string, password: string): Promise<MessageResponse> {
	return apiFetch<MessageResponse>("/v1/auth/change-email", {
		method: "POST",
		body: JSON.stringify({ new_email: newEmail, password }),
	});
}

/** POST /v1/auth/confirm-email-change — apply the change from the emailed token. */
export function confirmEmailChange(token: string): Promise<MessageResponse> {
	return apiFetch<MessageResponse>("/v1/auth/confirm-email-change", {
		method: "POST",
		body: JSON.stringify({ token }),
	});
}

/** GET /v1/auth/sessions — the caller's active sessions (devices), newest first. */
export function listSessions(): Promise<SessionInfo[]> {
	return apiFetch<SessionInfo[]>("/v1/auth/sessions");
}

/** DELETE /v1/auth/sessions/{id} — sign out one device (owner-scoped). */
export function revokeSession(publicId: string): Promise<void> {
	return apiFetch<void>(`/v1/auth/sessions/${publicId}`, { method: "DELETE" });
}

/** POST /v1/auth/delete-account — permanent erasure after password re-auth. */
export function deleteAccount(password: string): Promise<MessageResponse> {
	return apiFetch<MessageResponse>("/v1/auth/delete-account", {
		method: "POST",
		body: JSON.stringify({ password }),
	});
}

/**
 * GET /v1/auth/me/export — trigger a browser download of the portable JSON dump.
 * Uses the raw auth-retry fetch (not `apiFetch`) so we can turn the response
 * into a Blob and save it rather than parse it as a typed value.
 */
export async function downloadExport(): Promise<void> {
	const res = await fetchWithAuthRetry("/v1/auth/me/export");
	if (!res.ok) {
		throw new Error(`Export failed (${res.status})`);
	}
	const blob = await res.blob();
	const url = URL.createObjectURL(blob);
	try {
		const a = document.createElement("a");
		a.href = url;
		a.download = "slate-account-export.json";
		document.body.appendChild(a);
		a.click();
		a.remove();
	} finally {
		URL.revokeObjectURL(url);
	}
}
