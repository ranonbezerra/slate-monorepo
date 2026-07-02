import { Button, Card, Group, Stack, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { ApiError } from "@slate/shared/api";
import { IconBrandSteam, IconDownload } from "@tabler/icons-react";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { importSteamLibrary, steamStart } from "../lib/steam-api";

// ---------------------------------------------------------------------------
// Steam account-sync (Epic 30): connect a Steam account once via OpenID, then
// import owned games + playtime. A private profile can't be read, so we surface
// a friendly hint in that case rather than a hard error.
// ---------------------------------------------------------------------------

/** A 409 from the import route means Steam hasn't been linked yet. */
function isNotConnected(err: unknown): boolean {
	return err instanceof ApiError && err.status === 409;
}

export function SteamSyncSection() {
	const [connecting, setConnecting] = useState(false);

	const handleConnect = async () => {
		setConnecting(true);
		try {
			// Full-page navigate — the browser must actually travel to Steam's OpenID
			// endpoint, so we can't do this with a fetch.
			const { redirect_url } = await steamStart();
			window.location.href = redirect_url;
		} catch (err) {
			setConnecting(false);
			notifications.show({
				title: "Couldn't start Steam sign-in",
				message: err instanceof Error ? err.message : "Try again in a moment",
				color: "red",
			});
		}
	};

	const importMutation = useMutation({
		mutationFn: importSteamLibrary,
		onSuccess: (summary) => {
			if (summary.private_or_empty) {
				notifications.show({
					title: "No games found",
					message: "Make sure your Steam profile's game details are public, then try again.",
					color: "yellow",
				});
				return;
			}
			notifications.show({
				title: "Steam library imported",
				message: `Imported ${summary.imported} games (${summary.already_owned} already in your library, ${summary.unmatched} not matched).`,
				color: "green",
			});
		},
		onError: (err) => {
			if (isNotConnected(err)) {
				notifications.show({
					title: "Steam isn't connected",
					message: "Connect your Steam account first, then import your library.",
					color: "yellow",
				});
				return;
			}
			notifications.show({
				title: "Couldn't import Steam library",
				message: err instanceof Error ? err.message : "Try again in a moment",
				color: "red",
			});
		},
	});

	return (
		<Card shadow="sm" padding="xl" radius="md" maw={520}>
			<Title order={3} mb="xs">
				Steam
			</Title>
			<Text c="dimmed" size="sm" mb="lg">
				Connect your Steam account once, then import pulls your owned games and playtime into your
				library. Your profile's game details must be public — a private profile can't be read.
			</Text>
			<Stack>
				<Button
					variant="light"
					leftSection={<IconBrandSteam size={16} />}
					onClick={handleConnect}
					loading={connecting}
					style={{ alignSelf: "flex-start" }}
				>
					Connect Steam
				</Button>

				<Group>
					<Button
						leftSection={<IconDownload size={16} />}
						onClick={() => importMutation.mutate()}
						loading={importMutation.isPending}
						style={{ alignSelf: "flex-start" }}
					>
						Import my Steam library
					</Button>
				</Group>
			</Stack>
		</Card>
	);
}
