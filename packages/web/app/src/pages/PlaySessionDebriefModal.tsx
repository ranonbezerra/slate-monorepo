import { Button, Group, Modal, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { useEndPlaySession, useSubmitDebrief } from "../hooks/usePlaySession";
import type { PlaySession } from "../types/play-session";

interface PlaySessionDebriefModalProps {
	playSession: PlaySession | null;
	onClose: () => void;
}

export function PlaySessionDebriefModal({ playSession, onClose }: PlaySessionDebriefModalProps) {
	const [debriefText, setDebriefText] = useState("");
	const submitDebrief = useSubmitDebrief();
	const endPlaySession = useEndPlaySession();

	if (!playSession) return null;

	const handleDebrief = async () => {
		try {
			await submitDebrief.mutateAsync({
				publicId: playSession.publicId,
				debriefText,
			});
			notifications.show({
				title: "Session complete",
				message: "Your wrap-up has been saved. See you next session!",
				color: "green",
			});
			setDebriefText("");
			onClose();
		} catch (err) {
			notifications.show({
				title: "Couldn't save your wrap-up",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	const handleEndWithoutDebrief = async () => {
		try {
			await endPlaySession.mutateAsync({ publicId: playSession.publicId });
			notifications.show({
				title: "Session ended",
				message: "Session ended without a wrap-up.",
				color: "yellow",
			});
			setDebriefText("");
			onClose();
		} catch (err) {
			notifications.show({
				title: "Couldn't end session",
				message: err instanceof Error ? err.message : "An unexpected error occurred",
				color: "red",
			});
		}
	};

	return (
		<Modal
			opened={!!playSession}
			onClose={onClose}
			title={<Title order={4}>End session: {playSession.libraryEntry.game.title}</Title>}
			size="lg"
		>
			<Stack gap="md">
				<Text size="sm">
					What happened this session? Jot a quick wrap-up so your next recap knows where you left
					off.
				</Text>

				<Textarea
					placeholder="Beat the Mantis Lords. Got the cloak. Heading to Greenpath next..."
					value={debriefText}
					onChange={(e) => setDebriefText(e.currentTarget.value)}
					autosize
					minRows={4}
					maxRows={8}
				/>

				<Group justify="space-between">
					<Button
						variant="subtle"
						color="gray"
						onClick={handleEndWithoutDebrief}
						loading={endPlaySession.isPending}
					>
						Skip wrap-up
					</Button>
					<Button
						onClick={handleDebrief}
						loading={submitDebrief.isPending}
						disabled={debriefText.trim().length < 3}
					>
						Save wrap-up
					</Button>
				</Group>
			</Stack>
		</Modal>
	);
}
