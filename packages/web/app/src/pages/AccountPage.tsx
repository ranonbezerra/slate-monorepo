import { Stack, Tabs, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	IconDatabaseCog,
	IconDeviceLaptop,
	IconPlugConnected,
	IconShieldLock,
	IconUser,
} from "@tabler/icons-react";
import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { FEATURES } from "../lib/features";
import { ChangePasswordPage } from "./ChangePasswordPage";
import { DataPrivacySection } from "./DataPrivacySection";
import { EmailSection } from "./EmailSection";
import { MfaSection } from "./MfaSection";
import { ProfileSection } from "./ProfileSection";
import { SessionsSection } from "./SessionsSection";
import { SteamSyncSection } from "./SteamSyncSection";

// ---------------------------------------------------------------------------
// /account — settings, organized into tabs:
//   • Profile        → display name, language, timezone, email address
//   • Security       → change password + two-factor
//   • Sessions       → active devices
//   • Connections    → Steam account-sync (feature-flagged)
//   • Data & privacy → export + account deletion
// ---------------------------------------------------------------------------

export function AccountPage() {
	const [searchParams, setSearchParams] = useSearchParams();

	// The Steam OpenID flow redirects the browser back here with `?steam=…`.
	// Surface a human message once, then clear the param so a reload/back-nav
	// doesn't re-toast.
	useEffect(() => {
		const steam = searchParams.get("steam");
		if (!steam) return;
		if (steam === "connected") {
			notifications.show({
				title: "Steam connected",
				message: "You can import your library now.",
				color: "green",
			});
		} else {
			notifications.show({
				title: "Couldn't connect Steam",
				message: "Something went wrong linking your Steam account. Please try again.",
				color: "red",
			});
		}
		setSearchParams({}, { replace: true });
	}, [searchParams, setSearchParams]);

	return (
		<Stack gap="lg">
			<Title order={2}>Settings</Title>
			<Tabs defaultValue="profile" keepMounted={false}>
				<Tabs.List mb="lg">
					<Tabs.Tab value="profile" leftSection={<IconUser size={16} />}>
						Profile
					</Tabs.Tab>
					<Tabs.Tab value="security" leftSection={<IconShieldLock size={16} />}>
						Security
					</Tabs.Tab>
					<Tabs.Tab value="sessions" leftSection={<IconDeviceLaptop size={16} />}>
						Sessions
					</Tabs.Tab>
					{FEATURES.steamImport && (
						<Tabs.Tab value="connections" leftSection={<IconPlugConnected size={16} />}>
							Connections
						</Tabs.Tab>
					)}
					<Tabs.Tab value="data" leftSection={<IconDatabaseCog size={16} />}>
						Data &amp; privacy
					</Tabs.Tab>
				</Tabs.List>

				<Tabs.Panel value="profile">
					<Stack gap="lg">
						<ProfileSection />
						<EmailSection />
					</Stack>
				</Tabs.Panel>

				<Tabs.Panel value="security">
					<Stack gap="lg">
						<ChangePasswordPage />
						<MfaSection />
					</Stack>
				</Tabs.Panel>

				<Tabs.Panel value="sessions">
					<SessionsSection />
				</Tabs.Panel>

				{FEATURES.steamImport && (
					<Tabs.Panel value="connections">
						<SteamSyncSection />
					</Tabs.Panel>
				)}

				<Tabs.Panel value="data">
					<DataPrivacySection />
				</Tabs.Panel>
			</Tabs>
		</Stack>
	);
}
