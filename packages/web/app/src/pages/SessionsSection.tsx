import { Badge, Button, Card, Group, Loader, Stack, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconDeviceLaptop } from "@tabler/icons-react";
import { useSessions } from "../hooks/useAccount";
import type { SessionInfo } from "../types/auth";

// ---------------------------------------------------------------------------
// Active sessions: list the caller's devices and sign any of them out. The
// current device isn't specially flagged by the API — revoking it simply ends
// this session on the next refresh.
// ---------------------------------------------------------------------------

function formatWhen(iso: string | null): string {
	if (!iso) return "never";
	const d = new Date(iso);
	return Number.isNaN(d.getTime()) ? "unknown" : d.toLocaleString();
}

function SessionRow({
	session,
	onRevoke,
	revoking,
}: {
	session: SessionInfo;
	onRevoke: () => void;
	revoking: boolean;
}) {
	return (
		<Group justify="space-between" wrap="nowrap">
			<Group gap="sm" wrap="nowrap">
				<IconDeviceLaptop size={20} />
				<div>
					<Text size="sm" fw={600}>
						{session.device_label || "Unknown device"}
					</Text>
					<Text size="xs" c="dimmed">
						Last used {formatWhen(session.last_used_at)} · started {formatWhen(session.created_at)}
					</Text>
				</div>
			</Group>
			<Button size="xs" variant="light" color="red" onClick={onRevoke} loading={revoking}>
				Sign out
			</Button>
		</Group>
	);
}

export function SessionsSection() {
	const { sessions, isLoading, revoke, isRevoking, revokingId } = useSessions();

	const handleRevoke = async (publicId: string) => {
		try {
			await revoke(publicId);
			notifications.show({
				title: "Signed out",
				message: "That device was signed out.",
				color: "blue",
			});
		} catch (err) {
			notifications.show({
				title: "Couldn't sign out that device",
				message: err instanceof Error ? err.message : "Try again in a moment",
				color: "red",
			});
		}
	};

	return (
		<Card shadow="sm" padding="xl" radius="md" maw={520}>
			<Group justify="space-between" mb="xs">
				<Title order={3}>Active sessions</Title>
				<Badge color="gray">{sessions.length}</Badge>
			</Group>
			<Text c="dimmed" size="sm" mb="lg">
				Devices currently signed in to your account. Sign out anything you don't recognize.
			</Text>
			{isLoading ? (
				<Group justify="center" py="md">
					<Loader size="sm" />
				</Group>
			) : sessions.length === 0 ? (
				<Text size="sm" c="dimmed">
					No active sessions.
				</Text>
			) : (
				<Stack gap="md">
					{sessions.map((s) => (
						<SessionRow
							key={s.public_id}
							session={s}
							onRevoke={() => handleRevoke(s.public_id)}
							revoking={isRevoking && revokingId === s.public_id}
						/>
					))}
				</Stack>
			)}
		</Card>
	);
}
