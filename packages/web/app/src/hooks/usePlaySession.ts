import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
	endPlaySession,
	getActivePlaySession,
	getPlaySession,
	listPlaySessions,
	previewRecap,
	type RecapMode,
	regenerateRecap,
	startPlaySession,
	submitDebrief,
	submitRetroactiveDebrief,
} from "../lib/play-session-api";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

const MISSIONS_KEY = ["playSessions"] as const;
const LIBRARY_KEY = ["library"] as const;
const STATS_KEY = ["stats"] as const;

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function usePlaySessions(params?: { limit?: number; offset?: number }) {
	return useQuery({
		queryKey: [...MISSIONS_KEY, params],
		queryFn: () => listPlaySessions(params),
	});
}

export function usePlaySession(publicId: string) {
	return useQuery({
		queryKey: [...MISSIONS_KEY, publicId],
		queryFn: () => getPlaySession(publicId),
		enabled: !!publicId,
	});
}

export function useActivePlaySession() {
	return useQuery({
		queryKey: [...MISSIONS_KEY, "active"],
		queryFn: () => getActivePlaySession(),
	});
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function usePreviewRecap() {
	return useMutation({
		mutationFn: (vars: {
			libraryEntryPublicId: string;
			positionOverride?: string;
			mode?: RecapMode;
			signal?: AbortSignal;
		}) => previewRecap(vars.libraryEntryPublicId, vars.positionOverride, vars.mode, vars.signal),
	});
}

export function useRetroactiveDebrief() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { libraryEntryPublicId: string; debriefText: string }) =>
			submitRetroactiveDebrief(vars.libraryEntryPublicId, vars.debriefText),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: MISSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useStartPlaySession() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: {
			libraryEntryPublicId: string;
			recapText?: string;
			skipRecap?: boolean;
		}) => startPlaySession(vars.libraryEntryPublicId, vars.recapText, vars.skipRecap),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: MISSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useSubmitDebrief() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { publicId: string; debriefText: string }) =>
			submitDebrief(vars.publicId, vars.debriefText),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: MISSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useEndPlaySession() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { publicId: string; endedVia?: string }) =>
			endPlaySession(vars.publicId, vars.endedVia),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: MISSIONS_KEY });
			queryClient.invalidateQueries({ queryKey: LIBRARY_KEY });
			queryClient.invalidateQueries({ queryKey: STATS_KEY });
		},
	});
}

export function useRegenerateRecap() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (vars: { publicId: string; currentPosition?: string }) =>
			regenerateRecap(vars.publicId, vars.currentPosition),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: MISSIONS_KEY });
		},
	});
}
