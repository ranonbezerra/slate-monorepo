import { Alert, Card, Center, Group, Loader, Stack, Text, Title } from "@mantine/core";
import { IconCircleCheck, IconMailExclamation } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { confirmEmailChange } from "../lib/account-api";

type Status = "confirming" | "success" | "error" | "missing";

// ---------------------------------------------------------------------------
// /confirm-email-change — landing page for the link emailed to the NEW address.
//
// Reads `?token=`, POSTs it to /v1/auth/confirm-email-change (anonymous —
// the token is the credential), and shows a success or error state. Works
// whether or not the visitor happens to be signed in.
// ---------------------------------------------------------------------------

export function ConfirmEmailChangePage() {
	const [searchParams] = useSearchParams();
	const token = searchParams.get("token");
	const [status, setStatus] = useState<Status>(token ? "confirming" : "missing");
	// Single-use token: guard against StrictMode double-invocation.
	const attemptedRef = useRef(false);

	useEffect(() => {
		if (!token || attemptedRef.current) return;
		attemptedRef.current = true;

		confirmEmailChange(token)
			.then(() => setStatus("success"))
			.catch(() => setStatus("error"));
	}, [token]);

	return (
		<Center h="100vh">
			<Card shadow="md" padding="xl" radius="md" w={460}>
				<Stack>
					<Title order={2} ta="center">
						Email change
					</Title>

					{status === "confirming" && (
						<Group justify="center" py="md">
							<Loader />
							<Text c="dimmed">Confirming your new email…</Text>
						</Group>
					)}

					{status === "missing" && (
						<Alert color="yellow" icon={<IconMailExclamation size={18} />} title="Missing token">
							This link is missing its confirmation token. Open the most recent link from your
							email.
						</Alert>
					)}

					{status === "success" && (
						<Alert color="green" icon={<IconCircleCheck size={18} />} title="Email updated">
							Your email address has been updated.
						</Alert>
					)}

					{status === "error" && (
						<Alert
							color="red"
							icon={<IconMailExclamation size={18} />}
							title="Confirmation failed"
						>
							This confirmation link is invalid or has expired. Request the change again from your
							settings.
						</Alert>
					)}

					<Text ta="center" size="sm">
						<Link to="/account">Back to settings</Link>
					</Text>
				</Stack>
			</Card>
		</Center>
	);
}
