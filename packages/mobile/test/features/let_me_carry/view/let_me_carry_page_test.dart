import 'package:app/core/let_me_carry/let_me_carry_models.dart';
import 'package:app/core/let_me_carry/let_me_carry_repository.dart';
import 'package:app/core/theme/slate_theme.dart';
import 'package:app/features/let_me_carry/bloc/let_me_carry_bloc.dart';
import 'package:app/features/let_me_carry/view/let_me_carry_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockLetMeCarryRepository extends Mock implements LetMeCarryRepository {}

Stream<LetMeCarryDelta> _deltas(List<LetMeCarryDelta> items) async* {
  for (final item in items) {
    yield item;
  }
}

void main() {
  late MockLetMeCarryRepository repository;

  setUp(() {
    repository = MockLetMeCarryRepository();
  });

  Widget buildSubject() {
    return MaterialApp(
      theme: SlateTheme.dark,
      home: BlocProvider(
        create: (_) => LetMeCarryBloc(letMeCarryRepository: repository),
        child: const LetMeCarryPage(),
      ),
    );
  }

  testWidgets('shows the empty-state prompt', (tester) async {
    await tester.pumpWidget(buildSubject());

    expect(find.text('What should you play tonight?'), findsOneWidget);
  });

  testWidgets('sends a message and renders the streamed reply', (tester) async {
    when(
      () => repository.streamChat(
        message: any(named: 'message'),
        threadId: any(named: 'threadId'),
        cancelToken: any(named: 'cancelToken'),
      ),
    ).thenAnswer(
      (_) => _deltas(const [
        LetMeCarryDelta(token: 'Try Hades.'),
        LetMeCarryDelta(done: true, threadId: 't1'),
      ]),
    );

    await tester.pumpWidget(buildSubject());

    await tester.enterText(find.byType(TextField), 'something short');
    await tester.testTextInput.receiveAction(TextInputAction.send);
    await tester.pumpAndSettle();

    expect(find.text('something short'), findsOneWidget);
    expect(find.text('Try Hades.'), findsOneWidget);
  });

  testWidgets('renders a Play CTA for a validated recommendation', (
    tester,
  ) async {
    when(
      () => repository.streamChat(
        message: any(named: 'message'),
        threadId: any(named: 'threadId'),
        cancelToken: any(named: 'cancelToken'),
      ),
    ).thenAnswer(
      (_) => _deltas(const [
        LetMeCarryDelta(token: 'Give this a go.'),
        LetMeCarryDelta(
          recommendation: Recommendation(id: 'abc', title: 'Hades'),
        ),
        LetMeCarryDelta(done: true, threadId: 't1'),
      ]),
    );

    await tester.pumpWidget(buildSubject());
    await tester.enterText(find.byType(TextField), 'what should I play?');
    await tester.testTextInput.receiveAction(TextInputAction.send);
    await tester.pumpAndSettle();

    expect(find.text('Play Hades'), findsOneWidget);
  });
}
