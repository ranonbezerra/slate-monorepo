import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	changeEmail,
	deleteAccount,
	listSessions,
	revokeSession,
	updateProfile,
} from "../lib/account-api";
import type { SessionInfo, UpdateProfileInput } from "../types/auth";

const USER_QUERY_KEY = ["auth", "me"] as const;
const SESSIONS_KEY = ["auth", "sessions"] as const;

/**
 * Profile editing for the settings page. On success it refreshes the cached
 * `/me` user so the rest of the app sees the new display name / locale / tz.
 */
export function useUpdateProfile() {
	const queryClient = useQueryClient();
	const mutation = useMutation({
		mutationFn: (body: UpdateProfileInput) => updateProfile(body),
		onSuccess: (user) => {
			// Keep the normalized `emailVerified` mirror the /me query adds.
			queryClient.setQueryData(USER_QUERY_KEY, { ...user, emailVerified: user.email_verified });
		},
	});
	return {
		updateProfile: (body: UpdateProfileInput) => mutation.mutateAsync(body),
		isPending: mutation.isPending,
	};
}

/** Request an email change: re-auth + confirm link sent to the new address. */
export function useChangeEmail() {
	const mutation = useMutation({
		mutationFn: (vars: { newEmail: string; password: string }) =>
			changeEmail(vars.newEmail, vars.password),
	});
	return {
		changeEmail: (newEmail: string, password: string) =>
			mutation.mutateAsync({ newEmail, password }),
		isPending: mutation.isPending,
	};
}

/** Active-session (device) list plus a revoke mutation that refreshes the list. */
export function useSessions() {
	const queryClient = useQueryClient();
	const { data: sessions = [], isLoading } = useQuery<SessionInfo[]>({
		queryKey: SESSIONS_KEY,
		queryFn: listSessions,
		staleTime: 30 * 1000,
	});
	const revokeMutation = useMutation({
		mutationFn: (publicId: string) => revokeSession(publicId),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: SESSIONS_KEY }),
	});
	return {
		sessions,
		isLoading,
		revoke: (publicId: string) => revokeMutation.mutateAsync(publicId),
		isRevoking: revokeMutation.isPending,
		revokingId: revokeMutation.variables ?? null,
	};
}

/** Permanent account erasure after password re-authentication. */
export function useDeleteAccount() {
	const mutation = useMutation({
		mutationFn: (password: string) => deleteAccount(password),
	});
	return {
		deleteAccount: (password: string) => mutation.mutateAsync(password),
		isPending: mutation.isPending,
	};
}
