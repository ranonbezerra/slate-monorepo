// ---------------------------------------------------------------------------
// Feature flags — read from VITE_-prefixed env vars, default OFF.
// ---------------------------------------------------------------------------

function flag(value: unknown): boolean {
	return value === "true" || value === "1";
}

export const FEATURES = {
	// let_me_carry chat (Epic 11). Off by default until the agent is
	// validated against a real tool-calling model.
	letMeCarry: flag(
		typeof import.meta !== "undefined" && import.meta.env?.VITE_ENABLE_LET_ME_CARRY,
	),
} as const;
