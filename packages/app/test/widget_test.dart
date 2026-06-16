import 'package:app/app/app.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('App renders DailyLoadout title', (WidgetTester tester) async {
    await tester.pumpWidget(const App());
    await tester.pumpAndSettle();

    expect(find.text('DailyLoadout'), findsWidgets);
    expect(find.text('WIP'), findsOneWidget);
  });
}
