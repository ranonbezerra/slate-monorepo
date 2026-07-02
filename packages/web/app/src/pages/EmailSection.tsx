import { Button, Card, Group, PasswordInput, Stack, Text, TextInput, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useAuthContext } from "../contexts/AuthContext";
import { useChangeEmail } from "../hooks/useAccount";

// ---------------------------------------------------------------------------
// Email settings: shows the current address and requests a change. The new
// address only takes effect once the user clicks the confirm link we email —
// see ConfirmEmailChangePage.
// ---------------------------------------------------------------------------

interface EmailFormValues {
	newEmail: string;
	password: string;
}

export function EmailSection() {
	const { user } = useAuthContext();
	const { changeEmail, isPending } = useChangeEmail();

	const form = useForm<EmailFormValues>({
		initialValues: { newEmail: "", password: "" },
		validate: {
			newEmail: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Invalid email"),
			password: (v) => (v.length >= 1 ? null : "Password is required"),
		},
	});

	const handleSubmit = async (values: EmailFormValues) => {
		try {
			await changeEmail(values.newEmail.trim(), values.password);
			form.reset();
			notifications.show({
				title: "Confirm your new email",
				message: "We sent a link to the new address. The change applies once you click it.",
				color: "blue",
			});
		} catch (err) {
			notifications.show({
				title: "Couldn't change email",
				message: err instanceof Error ? err.message : "Try again in a moment",
				color: "red",
			});
		}
	};

	return (
		<Card shadow="sm" padding="xl" radius="md" maw={460}>
			<Title order={3} mb="xs">
				Email address
			</Title>
			<Text c="dimmed" size="sm" mb="lg">
				Current:{" "}
				<Text span fw={600}>
					{user?.email ?? "—"}
				</Text>
			</Text>
			<form onSubmit={form.onSubmit(handleSubmit)}>
				<Stack>
					<TextInput
						label="New email"
						placeholder="you@example.com"
						{...form.getInputProps("newEmail")}
					/>
					<PasswordInput
						label="Current password"
						description="Confirm it's you before we send the change link."
						placeholder="Your password"
						{...form.getInputProps("password")}
					/>
					<Group justify="flex-end">
						<Button type="submit" loading={isPending}>
							Send confirmation link
						</Button>
					</Group>
				</Stack>
			</form>
		</Card>
	);
}
