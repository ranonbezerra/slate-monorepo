import { apiFetch } from "@slate/shared/api";

// ---------------------------------------------------------------------------
// Steam account-sync API (Epic 30) — link a Steam account via OpenID, then
// import owned games + playtime. Both routes are authenticated; `apiFetch`
// attaches the in-memory access token and transparently refreshes on 401.
// ---------------------------------------------------------------------------

/** Result of a library import: how many games were pulled in vs. skipped. */
export interface SteamImportSummary {
	imported: number;
	already_owned: number;
	unmatched: number;
	private_or_empty: boolean;
}

/**
 * GET /v1/auth/steam/start — begin the OpenID link flow. Returns the Steam URL
 * the browser must be sent to (a full-page navigate, not fetch). `503` when the
 * server has no STEAM_API_KEY configured.
 */
export function steamStart(): Promise<{ redirect_url: string }> {
	return apiFetch<{ redirect_url: string }>("/v1/auth/steam/start");
}

/**
 * POST /v1/library/steam/import — pull the caller's owned Steam games into the
 * library. `409` when Steam isn't linked yet, `503` when the feature is disabled.
 */
export function importSteamLibrary(): Promise<SteamImportSummary> {
	return apiFetch<SteamImportSummary>("/v1/library/steam/import", { method: "POST" });
}
