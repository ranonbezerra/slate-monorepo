import { Button, Card, Group, Select, Stack, Text, TextInput, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useAuthContext } from "../contexts/AuthContext";
import { useUpdateProfile } from "../hooks/useAccount";

// ---------------------------------------------------------------------------
// Profile settings: edit display name, locale, and timezone (PATCH /me).
// ---------------------------------------------------------------------------

// A short curated locale list — enough for launch, extend as we localize.
const LOCALE_OPTIONS = [
	{ value: "en", label: "English" },
	{ value: "en-US", label: "English (US)" },
	{ value: "en-GB", label: "English (UK)" },
	{ value: "pt-BR", label: "Português (Brasil)" },
	{ value: "es", label: "Español" },
	{ value: "fr", label: "Français" },
	{ value: "de", label: "Deutsch" },
];

/** All IANA timezones the browser knows, for a searchable Select. */
function timezoneOptions(): string[] {
	try {
		return Intl.supportedValuesOf("timeZone");
	} catch {
		return ["UTC"];
	}
}

interface ProfileFormValues {
	displayName: string;
	locale: string;
	timezone: string;
}

export function ProfileSection() {
	const { user } = useAuthContext();
	const { updateProfile, isPending } = useUpdateProfile();

	const form = useForm<ProfileFormValues>({
		initialValues: {
			displayName: user?.display_name ?? "",
			locale: user?.locale ?? "en",
			timezone: user?.timezone ?? "UTC",
		},
		validate: {
			displayName: (v) =>
				v.trim().length >= 2 ? null : "Display name must be at least 2 characters",
		},
	});

	const handleSubmit = async (values: ProfileFormValues) => {
		try {
			await updateProfile({
				display_name: values.displayName.trim(),
				locale: values.locale,
				timezone: values.timezone,
			});
			form.resetDirty();
			notifications.show({
				title: "Profile updated",
				message: "Your changes were saved.",
				color: "green",
			});
		} catch (err) {
			notifications.show({
				title: "Couldn't update profile",
				message: err instanceof Error ? err.message : "Try again in a moment",
				color: "red",
			});
		}
	};

	return (
		<Card shadow="sm" padding="xl" radius="md" maw={460}>
			<Title order={3} mb="xs">
				Profile
			</Title>
			<Text c="dimmed" size="sm" mb="lg">
				How you appear in Slate and how dates and language are shown.
			</Text>
			<form onSubmit={form.onSubmit(handleSubmit)}>
				<Stack>
					<TextInput
						label="Display name"
						placeholder="Your name"
						{...form.getInputProps("displayName")}
					/>
					<Select
						label="Language"
						data={LOCALE_OPTIONS}
						allowDeselect={false}
						{...form.getInputProps("locale")}
					/>
					<Select
						label="Timezone"
						searchable
						data={timezoneOptions()}
						allowDeselect={false}
						nothingFoundMessage="No match"
						{...form.getInputProps("timezone")}
					/>
					<Group justify="flex-end">
						<Button type="submit" loading={isPending} disabled={!form.isDirty()}>
							Save changes
						</Button>
					</Group>
				</Stack>
			</form>
		</Card>
	);
}
