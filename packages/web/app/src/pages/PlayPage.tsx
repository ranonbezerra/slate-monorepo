import { Card, SimpleGrid, Stack, Text, Title, Tooltip, UnstyledButton } from "@mantine/core";
import { IconDice3, IconHandClick, IconMessageChatbot } from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { useActivePlaySession } from "../hooks/usePlaySession";
import { FEATURES } from "../lib/features";

interface DoorCardProps {
	title: string;
	subtitle: string;
	icon: React.ReactNode;
	accent?: boolean;
	disabled?: boolean;
	onClick: () => void;
}

const DISABLED_REASON = "Finish your active session first";

function DoorCard({ title, subtitle, icon, accent, disabled, onClick }: DoorCardProps) {
	// Render as a real <button> (UnstyledButton) so the door is keyboard
	// focusable and fires on Enter/Space natively; the Card inside is purely
	// visual. For the disabled state we use aria-disabled (not the native
	// `disabled` attribute) so the element stays focusable/hoverable and its
	// Tooltip reason remains reachable by both keyboard and pointer.
	const card = (
		<UnstyledButton
			onClick={disabled ? undefined : onClick}
			aria-disabled={disabled}
			aria-label={disabled ? `${title} — ${DISABLED_REASON}` : title}
			style={{
				cursor: disabled ? "not-allowed" : "pointer",
				height: "100%",
				width: "100%",
				display: "block",
				textAlign: "left",
			}}
		>
			<Card
				withBorder
				p="lg"
				radius="md"
				h="100%"
				style={{ opacity: disabled ? 0.55 : 1 }}
				bg={accent && !disabled ? "var(--mantine-primary-color-light)" : undefined}
			>
				<Stack gap="sm" align="flex-start">
					{icon}
					<Title order={4}>{title}</Title>
					<Text size="sm" c="dimmed">
						{subtitle}
					</Text>
				</Stack>
			</Card>
		</UnstyledButton>
	);

	if (disabled) {
		return (
			<Tooltip label={DISABLED_REASON} withArrow>
				{card}
			</Tooltip>
		);
	}
	return card;
}

export function PlayPage() {
	const navigate = useNavigate();
	const { data: activePlaySession } = useActivePlaySession();
	const hasActivePlaySession = Boolean(activePlaySession);

	return (
		<Stack maw={720} mx="auto" mt="md">
			<Title order={2}>Play</Title>
			<Text c="dimmed" size="sm">
				Pick how you want to start your session.
			</Text>

			<SimpleGrid cols={{ base: 1, sm: FEATURES.letMeCarry ? 3 : 2 }} mt="sm">
				<DoorCard
					title="What's the move?"
					subtitle="One tap — we pick, you play."
					icon={<IconDice3 size={28} />}
					accent
					disabled={hasActivePlaySession}
					onClick={() => navigate("/play/pick")}
				/>
				<DoorCard
					title="I'll choose"
					subtitle="Pick a game yourself."
					icon={<IconHandClick size={28} />}
					disabled={hasActivePlaySession}
					onClick={() => navigate("/library")}
				/>
				{FEATURES.letMeCarry && (
					<DoorCard
						title="Ask"
						subtitle="Chat about what to play."
						icon={<IconMessageChatbot size={28} />}
						onClick={() => navigate("/play/let-me-carry")}
					/>
				)}
			</SimpleGrid>
		</Stack>
	);
}
