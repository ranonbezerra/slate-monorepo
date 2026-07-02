import { Badge, Button, Group, Image, Paper, Stack, Text } from "@mantine/core";
import { IconBook, IconFlagCheck, IconWand } from "@tabler/icons-react";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useActivePlaySession } from "../hooks/usePlaySession";
import { FEATURES } from "../lib/features";
import { safeImageUrl } from "../lib/safe-image";
import { PlaySessionRecapModal } from "../pages/PlaySessionRecapModal";
import { PlaySessionWrapUpModal } from "../pages/PlaySessionWrapUpModal";

dayjs.extend(relativeTime);

// ---------------------------------------------------------------------------
// Global "active mission" bar.
//
// There is exactly one active play session per user. This bar floats fixed to
// the bottom of every authenticated screen while a session is active, so the
// player can always reach their wrap-up / recap actions. It owns the wrap-up +
// recap modal state itself so no page needs to re-implement the tracker.
// ---------------------------------------------------------------------------

export function ActiveMissionBar() {
	const navigate = useNavigate();
	const { data: activePlaySession } = useActivePlaySession();
	const [showRecap, setShowRecap] = useState(false);
	const [showWrapUp, setShowWrapUp] = useState(false);

	if (!activePlaySession) return null;

	const { game } = activePlaySession.libraryEntry;
	const cover = safeImageUrl(game.coverUrl);

	return (
		<>
			<Paper
				withBorder
				shadow="md"
				p="sm"
				radius={0}
				style={{
					position: "fixed",
					bottom: 0,
					left: 0,
					right: 0,
					zIndex: 200,
				}}
			>
				<Group justify="space-between" wrap="nowrap" gap="md">
					<Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
						{cover && <Image src={cover} alt={game.title} w={32} h={44} radius="sm" />}
						<Stack gap={2} style={{ minWidth: 0 }}>
							<Text fw={600} truncate>
								{game.title}
							</Text>
							<Group gap="xs" wrap="nowrap">
								<Badge color="teal" variant="dot" size="sm">
									Session active
								</Badge>
								<Text size="xs" c="dimmed">
									started {dayjs(activePlaySession.startedAt).fromNow()}
								</Text>
							</Group>
						</Stack>
					</Group>

					<Group gap="xs" wrap="nowrap">
						{FEATURES.letMeCarry && (
							<Button
								size="xs"
								variant="light"
								leftSection={<IconWand size={16} />}
								onClick={() => navigate("/play/let-me-carry")}
							>
								Carry me!
							</Button>
						)}
						{activePlaySession.recapText && (
							<Button
								size="xs"
								variant="light"
								leftSection={<IconBook size={16} />}
								onClick={() => setShowRecap(true)}
							>
								Recap
							</Button>
						)}
						<Button
							size="xs"
							color="teal"
							leftSection={<IconFlagCheck size={16} />}
							onClick={() => setShowWrapUp(true)}
						>
							Wrap up
						</Button>
					</Group>
				</Group>
			</Paper>

			{showRecap && activePlaySession.recapText && (
				<PlaySessionRecapModal
					mode="view"
					playSession={activePlaySession}
					onClose={() => setShowRecap(false)}
				/>
			)}
			<PlaySessionWrapUpModal
				playSession={showWrapUp ? activePlaySession : null}
				onClose={() => setShowWrapUp(false)}
			/>
		</>
	);
}
