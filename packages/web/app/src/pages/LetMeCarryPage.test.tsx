import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { LetMeCarryEvent } from "../types/let-me-carry";
import { LetMeCarryPage } from "./LetMeCarryPage";

const streamLetMeCarry = vi.fn();
const fetchLibraryEntry = vi.fn();

vi.mock("../lib/let-me-carry-api", () => ({
	streamLetMeCarry: (...args: unknown[]) => streamLetMeCarry(...args),
}));

vi.mock("../lib/library-api", async (importOriginal) => ({
	...(await importOriginal<typeof import("../lib/library-api")>()),
	fetchLibraryEntry: (...args: unknown[]) => fetchLibraryEntry(...args),
}));

async function* events(items: LetMeCarryEvent[]): AsyncGenerator<LetMeCarryEvent> {
	for (const item of items) yield item;
}

function renderPage() {
	const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
	return render(
		<QueryClientProvider client={client}>
			<MantineProvider>
				<MemoryRouter>
					<LetMeCarryPage />
				</MemoryRouter>
			</MantineProvider>
		</QueryClientProvider>,
	);
}

afterEach(() => {
	streamLetMeCarry.mockReset();
	fetchLibraryEntry.mockReset();
});

describe("LetMeCarryPage", () => {
	it("renders the empty state prompt", () => {
		renderPage();
		expect(screen.getByText("What should you play tonight?")).toBeInTheDocument();
	});

	it("sends a message and shows the streamed reply", async () => {
		streamLetMeCarry.mockReturnValue(
			events([{ token: "Try Hades." }, { done: true, thread_id: "t1" }]),
		);

		renderPage();
		const input = screen.getByPlaceholderText("Ask let_me_carry…");
		fireEvent.change(input, { target: { value: "something short" } });
		fireEvent.keyDown(input, { key: "Enter" });

		await waitFor(() => expect(screen.getByText("something short")).toBeInTheDocument());
		await waitFor(() => expect(screen.getByText("Try Hades.")).toBeInTheDocument());
		expect(streamLetMeCarry).toHaveBeenCalledWith(
			"something short",
			undefined,
			expect.any(AbortSignal),
		);
	});

	it("renders a Play CTA for a validated recommendation", async () => {
		streamLetMeCarry.mockReturnValue(
			events([
				{ token: "Give this a go." },
				{ recommendation: { id: "abc", title: "Hades" } },
				{ done: true, thread_id: "t1" },
			]),
		);

		renderPage();
		const input = screen.getByPlaceholderText("Ask let_me_carry…");
		fireEvent.change(input, { target: { value: "what should I play?" } });
		fireEvent.keyDown(input, { key: "Enter" });

		await waitFor(() =>
			expect(screen.getByRole("button", { name: /Play Hades/ })).toBeInTheDocument(),
		);
	});

	it("opens the recap-choice dialog when the Play CTA is clicked", async () => {
		streamLetMeCarry.mockReturnValue(
			events([
				{ token: "Give this a go." },
				{ recommendation: { id: "entry-1", title: "Hades" } },
				{ done: true, thread_id: "t1" },
			]),
		);
		// The CTA fetches the full entry, then opens the recap modal for it.
		fetchLibraryEntry.mockResolvedValue({
			publicId: "entry-1",
			game: { title: "Hades" },
			platform: { id: 1, label: "PC" },
			status: "playing",
		});

		renderPage();
		const input = screen.getByPlaceholderText("Ask let_me_carry…");
		fireEvent.change(input, { target: { value: "what should I play?" } });
		fireEvent.keyDown(input, { key: "Enter" });

		const playButton = await screen.findByRole("button", { name: /Play Hades/ });
		fireEvent.click(playButton);

		// The recap-choice dialog opens for the recommended game.
		await waitFor(() => expect(fetchLibraryEntry).toHaveBeenCalledWith("entry-1"));
		await waitFor(() => expect(screen.getByText("Recap: Hades")).toBeInTheDocument());
		expect(screen.getByText(/Quick recap/)).toBeInTheDocument();
	});

	it("shows the typing indicator while the reply is pending", async () => {
		let release: () => void = () => {};
		const gate = new Promise<void>((resolve) => {
			release = resolve;
		});
		async function* gated(): AsyncGenerator<LetMeCarryEvent> {
			await gate;
			yield { token: "Done." };
			yield { done: true, thread_id: "t1" };
		}
		streamLetMeCarry.mockReturnValue(gated());

		renderPage();
		const input = screen.getByPlaceholderText("Ask let_me_carry…");
		fireEvent.change(input, { target: { value: "hi" } });
		fireEvent.keyDown(input, { key: "Enter" });

		// Reply hasn't arrived yet → the animated typing indicator is visible.
		await waitFor(() =>
			expect(screen.getByLabelText("let_me_carry is thinking")).toBeInTheDocument(),
		);

		release();
		await waitFor(() => expect(screen.getByText("Done.")).toBeInTheDocument());
		expect(screen.queryByLabelText("let_me_carry is thinking")).not.toBeInTheDocument();
	});
});
