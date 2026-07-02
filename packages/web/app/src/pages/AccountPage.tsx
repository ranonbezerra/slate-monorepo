import { Stack, Tabs, Title } from "@mantine/core";
import { IconDatabaseCog, IconDeviceLaptop, IconShieldLock, IconUser } from "@tabler/icons-react";
import { ChangePasswordPage } from "./ChangePasswordPage";
import { DataPrivacySection } from "./DataPrivacySection";
import { EmailSection } from "./EmailSection";
import { MfaSection } from "./MfaSection";
import { ProfileSection } from "./ProfileSection";
import { SessionsSection } from "./SessionsSection";

// ---------------------------------------------------------------------------
// /account — settings, organized into tabs:
//   • Profile        → display name, language, timezone, email address
//   • Security       → change password + two-factor
//   • Sessions       → active devices
//   • Data & privacy → export + account deletion
// ---------------------------------------------------------------------------

export function AccountPage() {
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

				<Tabs.Panel value="data">
					<DataPrivacySection />
				</Tabs.Panel>
			</Tabs>
		</Stack>
	);
}
