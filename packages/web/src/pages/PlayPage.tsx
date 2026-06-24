import { Badge, Button, Card, Group, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { IconDice3, IconHandClick, IconMessageChatbot, IconPlayerPlay } from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { useActiveMission } from "../hooks/useMission";
import { FEATURES } from "../lib/features";

interface DoorCardProps {
	title: string;
	subtitle: string;
	icon: React.ReactNode;
	accent?: boolean;
	onClick: () => void;
}

function DoorCard({ title, subtitle, icon, accent, onClick }: DoorCardProps) {
	return (
		<Card
			withBorder
			p="lg"
			radius="md"
			onClick={onClick}
			style={{ cursor: "pointer", height: "100%" }}
			bg={accent ? "var(--mantine-primary-color-light)" : undefined}
		>
			<Stack gap="sm" align="flex-start">
				{icon}
				<Title order={4}>{title}</Title>
				<Text size="sm" c="dimmed">
					{subtitle}
				</Text>
			</Stack>
		</Card>
	);
}

export function PlayPage() {
	const navigate = useNavigate();
	const { data: activeMission } = useActiveMission();

	return (
		<Stack maw={720} mx="auto" mt="md">
			<Title order={2}>Play</Title>
			<Text c="dimmed" size="sm">
				Pick how you want to start your session.
			</Text>

			{activeMission ? (
				<Card withBorder p="lg" radius="md">
					<Stack gap="md">
						<Group justify="space-between" align="flex-start">
							<Group gap="sm">
								<Badge color="teal" variant="dot" size="lg">
									Mission active
								</Badge>
								<Title order={3}>{activeMission.libraryEntry.game.title}</Title>
							</Group>
						</Group>

						{activeMission.briefingText && (
							<Card withBorder p="sm" radius="sm">
								<Text size="sm" c="dimmed" lineClamp={3}>
									{activeMission.briefingText}
								</Text>
							</Card>
						)}

						<Group>
							<Button
								leftSection={<IconPlayerPlay size={18} />}
								onClick={() => navigate("/play/missions")}
							>
								Resume
							</Button>
							<Button variant="outline" color="teal" onClick={() => navigate("/play/missions")}>
								End / Debrief
							</Button>
						</Group>
					</Stack>
				</Card>
			) : (
				<Card withBorder p="lg" radius="md">
					<Text c="dimmed" ta="center" py="sm">
						No active mission. Choose a door below to get rolling.
					</Text>
				</Card>
			)}

			<SimpleGrid cols={{ base: 1, sm: FEATURES.backlogConcierge ? 3 : 2 }} mt="sm">
				<DoorCard
					title="What's the move?"
					subtitle="One tap — we pick, you play."
					icon={<IconDice3 size={28} />}
					accent
					onClick={() => navigate("/play/loadout")}
				/>
				<DoorCard
					title="I'll choose"
					subtitle="Pick a game yourself."
					icon={<IconHandClick size={28} />}
					onClick={() => navigate("/library")}
				/>
				{FEATURES.backlogConcierge && (
					<DoorCard
						title="Ask"
						subtitle="Chat about what to play."
						icon={<IconMessageChatbot size={28} />}
						onClick={() => navigate("/play/concierge")}
					/>
				)}
			</SimpleGrid>
		</Stack>
	);
}
