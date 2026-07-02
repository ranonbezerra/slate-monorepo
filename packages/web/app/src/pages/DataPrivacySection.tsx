import {
	Alert,
	Button,
	Card,
	Divider,
	Group,
	PasswordInput,
	Stack,
	Text,
	Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertTriangle, IconDownload } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthContext } from "../contexts/AuthContext";
import { useDeleteAccount } from "../hooks/useAccount";
import { downloadExport } from "../lib/account-api";

// ---------------------------------------------------------------------------
// Data & privacy (GDPR/LGPD): export a portable copy of your data, or
// permanently delete the account. Deletion re-authenticates with the password
// and is a two-step confirm to guard against accidental clicks.
// ---------------------------------------------------------------------------

export function DataPrivacySection() {
	const { logout } = useAuthContext();
	const { deleteAccount, isPending } = useDeleteAccount();
	const navigate = useNavigate();
	const [exporting, setExporting] = useState(false);
	const [confirming, setConfirming] = useState(false);
	const [password, setPassword] = useState("");

	const handleExport = async () => {
		setExporting(true);
		try {
			await downloadExport();
		} catch (err) {
			notifications.show({
				title: "Export failed",
				message: err instanceof Error ? err.message : "Try again in a moment",
				color: "red",
			});
		} finally {
			setExporting(false);
		}
	};

	const handleDelete = async () => {
		try {
			await deleteAccount(password);
			notifications.show({
				title: "Account deleted",
				message: "Your account and data were permanently removed.",
				color: "blue",
			});
			await logout();
			navigate("/login", { replace: true });
		} catch (err) {
			notifications.show({
				title: "Couldn't delete account",
				message: err instanceof Error ? err.message : "Check your password and try again",
				color: "red",
			});
		}
	};

	return (
		<Card shadow="sm" padding="xl" radius="md" maw={520}>
			<Title order={3} mb="xs">
				Data &amp; privacy
			</Title>
			<Text c="dimmed" size="sm" mb="lg">
				Download a copy of your data, or permanently delete your account.
			</Text>
			<Stack>
				<Button
					variant="light"
					leftSection={<IconDownload size={16} />}
					onClick={handleExport}
					loading={exporting}
					style={{ alignSelf: "flex-start" }}
				>
					Export my data
				</Button>

				<Divider my="sm" />

				<Alert color="red" icon={<IconAlertTriangle size={18} />} title="Delete account">
					<Text size="sm" mb="sm">
						This permanently erases your library, sessions, and history. It cannot be undone.
					</Text>
					{confirming ? (
						<Stack>
							<PasswordInput
								label="Confirm your password"
								placeholder="Your password"
								value={password}
								onChange={(e) => setPassword(e.currentTarget.value)}
							/>
							<Group justify="flex-end">
								<Button
									variant="default"
									onClick={() => {
										setConfirming(false);
										setPassword("");
									}}
								>
									Cancel
								</Button>
								<Button color="red" onClick={handleDelete} loading={isPending}>
									Permanently delete
								</Button>
							</Group>
						</Stack>
					) : (
						<Button color="red" variant="outline" onClick={() => setConfirming(true)}>
							Delete my account
						</Button>
					)}
				</Alert>
			</Stack>
		</Card>
	);
}
