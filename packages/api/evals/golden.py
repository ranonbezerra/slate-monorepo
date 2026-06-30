"""Golden dataset for the recap eval — 12 cases over a real library.

Each case is a snapshot of a real recap call: the player's prior notes go
straight into ``inputs`` (no DB seed), and ``reference`` carries the rubric the
checks + judge grade against. The cases are spread on purpose across four axes —
known/obscure to the model, amount of history, note quality, and spoiler surface
— so the set measures *quality*, not plumbing, when run against a real model.

Run against ``DummyLLMClient`` the scores are only trivially deterministic (the
dummy output is fixed); these cases are meant for a real model, where they grade
faithfulness, grounding, spoiler-safety, and recall.
"""

from __future__ import annotations

from evals.schema import EvalCase


def _recap_case(
    case_id: str,
    game: str,
    wrap_ups: list[str],
    next_action: str | None,
    *,
    mentions: list[str],
    forbidden: list[str],
    behavior: str,
) -> EvalCase:
    """Build a recap ``EvalCase`` from a case's notes + expectations.

    ``mentions`` (recall) must appear in the output; ``forbidden`` (spoilers)
    must not; ``context`` (notes + next action + title) is what the grounding
    check and the judge treat as the only source of truth.
    """
    context = " ".join([game, *wrap_ups, next_action or ""])
    return EvalCase(
        id=case_id,
        task="recap",
        inputs={
            "game_title": game,
            "previous_wrap_ups": [{"raw_text": w} for w in wrap_ups],
            "current_next_action": next_action,
        },
        reference={
            "context": context,
            "mentions": mentions,
            "forbidden": forbidden,
            "behavior": behavior,
        },
        checks=["non_empty", "grounding", "spoiler_free", "mentions"],
    )


def golden_cases() -> list[EvalCase]:
    """Return the curated golden recap cases (the set the eval tracks)."""
    return [
        # 1) known game, returning, clean notes, spoiler trap.
        _recap_case(
            "cyberpunk_act1_clean_spoiler",
            "Cyberpunk 2077",
            [
                "Finished the Konpeki Plaza heist; Jackie died in the escape. Woke up with Johnny's biochip in my head.",
                "Did gigs for Dexter that went bad, got shot and dumped in the landfill. Met Johnny Silverhand for real.",
                "In Watson doing jobs for Regina, saving up for the ripperdoc. Street cred rising, still early.",
            ],
            "go back to Watson and finish Regina's gigs before advancing the main quest",
            mentions=["Watson", "Regina", "Johnny"],
            forbidden=["Mikoshi", "Arasaka Tower", "Alt Cunningham", "ending"],
            behavior="Resume in Watson; treat as early game; do not anticipate later acts.",
        ),
        # 2) known, returning after a long pause, clean, spoiler trap.
        _recap_case(
            "elden_ring_returning_after_pause",
            "Elden Ring",
            [
                "Cleared Stormveil Castle, beat Godrick, took his great rune.",
                "Exploring Liurnia, found Raya Lucaria Academy but haven't entered. Rode Torrent around a lot.",
            ],
            "enter Raya Lucaria Academy and fight the academy boss",
            mentions=["Liurnia", "Raya Lucaria"],
            forbidden=["Malenia", "Maliketh", "Radagon", "Elden Beast"],
            behavior="Welcome the return with zero blame; reorient at Liurnia; no future bosses as if played.",
        ),
        # 3) known, FIRST session (empty history), spoiler trap — hardest hallucination test.
        _recap_case(
            "bg3_first_session_empty_history",
            "Baldur's Gate III",
            [],
            None,
            mentions=[],
            forbidden=["Moonrise", "Elder Brain", "Baldur's Gate", "Act 2", "Act 3"],
            behavior="Signal it is the first session / no prior recap; invent no progress, place, or boss.",
        ),
        # 4) obscure to the model, vague notes — opposite failure mode (inventing specificity).
        _recap_case(
            "digimon_next_order_obscure_vague",
            "Digimon World: Next Order",
            [
                "Played a bit, my digimon evolved. Was training them on the farm.",
                "Don't really remember where I stopped, maybe in a town looking for a quest.",
            ],
            "find the next quest in town",
            mentions=[],
            forbidden=["Machinedramon", "Server Desert", "WarGreymon"],
            behavior="Stay vague and honest; invent no areas, bosses, or Digimon not in the notes.",
        ),
        # 5) very new/obscure (2025), clean but sparse.
        _recap_case(
            "clair_obscur_new_sparse",
            "Clair Obscur: Expedition 33",
            [
                "Started Expedition 33. Left camp and fought the first enemies in turn-based combat with dodging.",
            ],
            "follow the trail after the first fight",
            mentions=["camp"],
            forbidden=["Paintress", "Gommage"],
            behavior="Reorient from the first fight; invent no advanced lore for this recent game.",
        ),
        # 6) live-service, no narrative, returning.
        _recap_case(
            "helldivers2_live_service_no_narrative",
            "Helldivers 2",
            [
                "Ran missions against the Terminids on medium. Unlocked a new orbital stratagem. Bumped my warbond.",
            ],
            "farm samples to unlock the next upgrade",
            mentions=["Terminids", "stratagem"],
            forbidden=["final boss", "story"],
            behavior="Focus on progress/loadout; do not invent a story where there is none.",
        ),
        # 7) known, noisy notes (typos, wrong boss name) — robustness to dirty input.
        _recap_case(
            "black_myth_noisy_input",
            "Black Myth: Wukong",
            [
                "still in ch 1, fought the guardian wolf (i think it's Guangzhi?) and died a few times",
                "got some spirits and upgraded the staff, gonna try the end-of-chapter boss again",
            ],
            "try the chapter 1 end boss again",
            mentions=["chapter 1"],
            forbidden=["Yellow Wind Sage", "chapter 3", "Erlang"],
            behavior="Clean the language but keep the uncertainty; don't invent the boss name or advance chapters.",
        ),
        # 8) known, EXTREME spoiler trap — highest-value spoiler case.
        _recap_case(
            "ff7_rebirth_extreme_spoiler_trap",
            "Final Fantasy VII Rebirth",
            [
                "Left Midgar, reached Kalm and saw Cloud's flashback about Nibelheim.",
                "Crossing the Grasslands doing Chadley's towers and taming chocobos. Junon ahead.",
            ],
            "head to Junon along the Grasslands road",
            mentions=["Grasslands", "Junon"],
            forbidden=["Aerith", "Forgotten Capital", "Forgotten City", "Sephiroth"],
            behavior="Resume from the Grasslands toward Junon; no beat from a later act.",
        ),
        # 9) clean, positive anchor — SHOULD score high (calibrates the ruler).
        _recap_case(
            "ghost_tsushima_clean_positive_anchor",
            "Ghost of Tsushima: Director's Cut",
            [
                "Started in Izuhara, freed some villagers and learned the first stance against the Mongols.",
                "Cleared a Mongol camp at night in stealth, raised resolve. Followed foxes to some shrines.",
            ],
            "keep liberating Izuhara and follow the main story trail",
            mentions=["Izuhara", "Mongol"],
            forbidden=["Tsushima fell", "Khotun Khan defeated"],
            behavior="Clean resume in Izuhara; this case should score high.",
        ),
        # 10) status COMPLETED — terminal-state edge case (no mandatory next step).
        _recap_case(
            "ff7_ever_crisis_completed_edge",
            "Final Fantasy VII: Ever Crisis",
            [
                "Finished the main available arc and completed the chapters that had released.",
                "Came back just to hit some limited-time events and farm materia.",
            ],
            None,
            mentions=[],
            forbidden=["next boss"],
            behavior="Acknowledge it is done / a casual return; do not fabricate a mandatory next step.",
        ),
        # 11) long, CONTRADICTORY history — conflict resolution.
        _recap_case(
            "little_nightmares_contradictory_history",
            "Little Nightmares",
            [
                "Got past the kitchen with the two fat cooks.",
                "I think I haven't reached the kitchen yet, was running from the long-armed janitor.",
                "Solved the shoes puzzle and moved on, but got stuck in a dark spot with a lantern.",
            ],
            "get past the dark area after the shoes",
            mentions=[],
            forbidden=["The Lady", "ending"],
            behavior="Prefer the most recent note / next_action; do not assert a disputed fact as settled.",
        ),
        # 12) live-service, minimal + vague signal — the floor (don't invent to fill).
        _recap_case(
            "cs2_minimal_signal",
            "Counter-Strike 2",
            [
                "Played some competitive, won some lost some. Nothing special.",
            ],
            None,
            mentions=[],
            forbidden=["campaign", "boss"],
            behavior="Keep it short and honest; invent no objective, rank, or plot.",
        ),
    ]
