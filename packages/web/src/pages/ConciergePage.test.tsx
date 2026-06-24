import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ConciergeEvent } from "../types/concierge";
import { ConciergePage } from "./ConciergePage";

const streamConcierge = vi.fn();

vi.mock("../lib/concierge-api", () => ({
	streamConcierge: (...args: unknown[]) => streamConcierge(...args),
}));

async function* events(items: ConciergeEvent[]): AsyncGenerator<ConciergeEvent> {
	for (const item of items) yield item;
}

function renderPage() {
	return render(
		<MantineProvider>
			<ConciergePage />
		</MantineProvider>,
	);
}

afterEach(() => {
	streamConcierge.mockReset();
});

describe("ConciergePage", () => {
	it("renders the empty state prompt", () => {
		renderPage();
		expect(screen.getByText("What should you play tonight?")).toBeInTheDocument();
	});

	it("sends a message and shows the streamed reply", async () => {
		streamConcierge.mockReturnValue(
			events([{ delta: "Try Hades." }, { done: true, thread_id: "t1" }]),
		);

		renderPage();
		const input = screen.getByPlaceholderText("Ask the concierge…");
		fireEvent.change(input, { target: { value: "something short" } });
		fireEvent.keyDown(input, { key: "Enter" });

		await waitFor(() => expect(screen.getByText("something short")).toBeInTheDocument());
		await waitFor(() => expect(screen.getByText("Try Hades.")).toBeInTheDocument());
		expect(streamConcierge).toHaveBeenCalledWith("something short", undefined);
	});

	it("shows the typing indicator while the reply is pending", async () => {
		let release: () => void = () => {};
		const gate = new Promise<void>((resolve) => {
			release = resolve;
		});
		async function* gated(): AsyncGenerator<ConciergeEvent> {
			await gate;
			yield { delta: "Done." };
			yield { done: true, thread_id: "t1" };
		}
		streamConcierge.mockReturnValue(gated());

		renderPage();
		const input = screen.getByPlaceholderText("Ask the concierge…");
		fireEvent.change(input, { target: { value: "hi" } });
		fireEvent.keyDown(input, { key: "Enter" });

		// Reply hasn't arrived yet → the animated typing indicator is visible.
		await waitFor(() =>
			expect(screen.getByLabelText("Concierge is thinking")).toBeInTheDocument(),
		);

		release();
		await waitFor(() => expect(screen.getByText("Done.")).toBeInTheDocument());
		expect(screen.queryByLabelText("Concierge is thinking")).not.toBeInTheDocument();
	});
});
