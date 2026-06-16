import { AppShell, Text, Title } from "@mantine/core";

function App() {
	return (
		<AppShell navbar={{ width: 250, breakpoint: "sm" }} padding="md">
			<AppShell.Navbar p="md">
				<Text fw={700}>Navigation</Text>
			</AppShell.Navbar>

			<AppShell.Main>
				<Title order={1}>DailyLoadout</Title>
			</AppShell.Main>
		</AppShell>
	);
}

export default App;
