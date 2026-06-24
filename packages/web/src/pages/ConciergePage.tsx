import {
	ActionIcon,
	Box,
	Card,
	Group,
	Loader,
	Paper,
	ScrollArea,
	Stack,
	Text,
	TextInput,
	Title,
} from "@mantine/core";
import { IconSend, IconSparkles } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";
import { useConcierge } from "../hooks/useConcierge";
import type { ChatMessage } from "../types/concierge";

const typingKeyframes = `
@keyframes conciergeBlink {
  0%, 80%, 100% { opacity: 0.25; transform: translateY(0); }
  40% { opacity: 1; transform: translateY(-3px); }
}
`;

const TYPING_DOTS = ["dot-0", "dot-1", "dot-2"];

function TypingDots() {
	return (
		<Group gap={5} py={4} aria-label="Concierge is thinking">
			{TYPING_DOTS.map((id, i) => (
				<Box
					key={id}
					w={7}
					h={7}
					style={{
						borderRadius: "50%",
						backgroundColor: "var(--mantine-color-gray-5)",
						animation: "conciergeBlink 1.2s infinite ease-in-out",
						animationDelay: `${i * 0.16}s`,
					}}
				/>
			))}
		</Group>
	);
}

function MessageBubble({ message }: { message: ChatMessage }) {
	const isUser = message.role === "user";
	const isPending = message.role === "assistant" && message.text === "";
	return (
		<Group justify={isUser ? "flex-end" : "flex-start"} align="flex-start" wrap="nowrap">
			<Card withBorder radius="lg" py="xs" px="md" maw="80%" bg={isUser ? "blue.9" : undefined}>
				{isPending ? (
					<TypingDots />
				) : (
					<Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
						{message.text}
					</Text>
				)}
			</Card>
		</Group>
	);
}

export function ConciergePage() {
	const { messages, isStreaming, error, send } = useConcierge();
	const [input, setInput] = useState("");
	const viewport = useRef<HTMLDivElement>(null);

	// Keep the latest message in view as the reply streams in. `messages` is the
	// intended trigger even though the body only reads the viewport ref.
	// biome-ignore lint/correctness/useExhaustiveDependencies: scroll on new messages
	useEffect(() => {
		viewport.current?.scrollTo?.({ top: viewport.current.scrollHeight, behavior: "smooth" });
	}, [messages]);

	const submit = () => {
		const text = input.trim();
		if (!text || isStreaming) return;
		setInput("");
		void send(text);
	};

	return (
		<Stack h="calc(100vh - 32px)" gap="md">
			{/* biome-ignore lint/security/noDangerouslySetInnerHtml: keyframe injection */}
			<style dangerouslySetInnerHTML={{ __html: typingKeyframes }} />
			<div>
				<Title order={2}>Backlog Concierge</Title>
				<Text c="dimmed" size="sm">
					Ask what to play — grounded in your library, sessions, and the time you have.
				</Text>
			</div>

			<ScrollArea style={{ flex: 1 }} viewportRef={viewport} type="auto">
				<Stack gap="sm" p="xs">
					{messages.length === 0 && (
						<Paper withBorder radius="lg" p="xl">
							<Stack align="center" gap="xs">
								<IconSparkles size={28} />
								<Text fw={600}>What should you play tonight?</Text>
								<Text c="dimmed" size="sm" ta="center">
									Try “I have 30 minutes and want something chill” or “What was I doing in my last
									RPG?”
								</Text>
							</Stack>
						</Paper>
					)}
					{messages.map((message, i) => (
						// Order-stable list that only ever grows; index key is safe here.
						// biome-ignore lint/suspicious/noArrayIndexKey: append-only chat log
						<MessageBubble key={i} message={message} />
					))}
				</Stack>
			</ScrollArea>

			{error && (
				<Text c="red" size="sm">
					{error}
				</Text>
			)}

			<Box>
				<TextInput
					placeholder="Ask the concierge…"
					value={input}
					onChange={(e) => setInput(e.currentTarget.value)}
					onKeyDown={(e) => {
						if (e.key === "Enter" && !e.shiftKey) {
							e.preventDefault();
							submit();
						}
					}}
					disabled={isStreaming}
					rightSection={
						isStreaming ? (
							<Loader size="xs" />
						) : (
							<ActionIcon
								variant="subtle"
								onClick={submit}
								disabled={!input.trim()}
								aria-label="Send message"
							>
								<IconSend size={18} />
							</ActionIcon>
						)
					}
				/>
			</Box>
		</Stack>
	);
}
