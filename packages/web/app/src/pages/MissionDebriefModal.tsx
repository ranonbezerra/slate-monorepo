import { Button, Group, Modal, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { useEndMission, useSubmitDebrief } from "../hooks/useMission";
import type { Mission } from "../types/mission";

interface MissionDebriefModalProps {
	mission: Mission | null;
	onClose: () => void;
}

export function MissionDebriefModal({ mission, onClose }: MissionDebriefModalProps) {
	const [debriefText, setDebriefText] = useState("");
	const submitDebrief = useSubmitDebrief();
	const endMission = useEndMission();

	if (!mission) return null;

	const handleDebrief = async () => {
		try {
			await submitDebrief.mutateAsync({
				publicId: mission.publicId,
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
			await endMission.mutateAsync({ publicId: mission.publicId });
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
			opened={!!mission}
			onClose={onClose}
			title={<Title order={4}>End session: {mission.libraryEntry.game.title}</Title>}
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
						loading={endMission.isPending}
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
