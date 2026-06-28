import 'package:app/core/library/library_models.dart';
import 'package:app/core/play_session/play_session_models.dart';
import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:flutter_test/flutter_test.dart';

final _now = DateTime.utc(2025, 6);

const _platform = Platform(id: 1, slug: 'ps5', label: 'PS5', family: 'sony');

final _game = Game(
  publicId: 'game-001',
  slug: 'elden-ring',
  title: 'Elden Ring',
  metadataSource: 'igdb',
  createdAt: _now,
);

final _entry = LibraryEntry(
  publicId: 'lib-001',
  game: _game,
  platform: _platform,
  status: 'playing',
  createdAt: _now,
  updatedAt: _now,
);

final _playSession = PlaySession(
  publicId: 'playSession-001',
  libraryEntry: _entry,
  playSessionType: 'new_game',
  startedAt: _now,
  createdAt: _now,
  updatedAt: _now,
  briefingText: 'Welcome back!',
);

final _listItem = PlaySessionListItem(
  publicId: 'playSession-001',
  libraryEntry: _entry,
  playSessionType: 'new_game',
  startedAt: _now,
);

final _preview = BriefingPreview(
  libraryEntry: _entry,
  briefingText: 'Your briefing',
);

void main() {
  group('PlaySessionEvent', () {
    test('LoadPlaySessions supports value equality and props', () {
      const a = LoadPlaySessions(limit: 10, offset: 5);
      const b = LoadPlaySessions(limit: 10, offset: 5);
      expect(a, b);
      expect(a.props, [10, 5]);
      expect(const LoadPlaySessions().props, [null, null]);
    });

    test('LoadMorePlaySessions supports value equality', () {
      expect(const LoadMorePlaySessions(), const LoadMorePlaySessions());
      expect(const LoadMorePlaySessions().props, isEmpty);
    });

    test('LoadActivePlaySession supports value equality', () {
      expect(const LoadActivePlaySession(), const LoadActivePlaySession());
      expect(const LoadActivePlaySession().props, isEmpty);
    });

    test('PreviewBriefing supports value equality and props', () {
      const a = PreviewBriefing(
        libraryEntryPublicId: 'lib-1',
        positionOverride: 'chapter 2',
        mode: 'deep',
      );
      const b = PreviewBriefing(
        libraryEntryPublicId: 'lib-1',
        positionOverride: 'chapter 2',
        mode: 'deep',
      );
      expect(a, b);
      expect(a.props, ['lib-1', 'chapter 2', 'deep']);
    });

    test('PreviewBriefing uses default mode', () {
      const a = PreviewBriefing(libraryEntryPublicId: 'lib-1');
      expect(a.mode, 'quick');
      expect(a.props, ['lib-1', null, 'quick']);
    });

    test('CancelDeepBriefing supports value equality and props', () {
      const a = CancelDeepBriefing(libraryEntryPublicId: 'lib-1');
      const b = CancelDeepBriefing(libraryEntryPublicId: 'lib-1');
      expect(a, b);
      expect(a.props, ['lib-1']);
    });

    test('StartPlaySession supports value equality and props', () {
      const a = StartPlaySession(
        libraryEntryPublicId: 'lib-1',
        briefingText: 'go',
      );
      const b = StartPlaySession(
        libraryEntryPublicId: 'lib-1',
        briefingText: 'go',
      );
      expect(a, b);
      expect(a.props, ['lib-1', 'go', false]);
      expect(const StartPlaySession(libraryEntryPublicId: 'lib-1').props, [
        'lib-1',
        null,
        false,
      ]);
      expect(
        const StartPlaySession(
          libraryEntryPublicId: 'lib-1',
          skipBriefing: true,
        ).props,
        ['lib-1', null, true],
      );
    });

    test('SubmitDebrief supports value equality and props', () {
      const a = SubmitDebrief(publicId: 'm-1', debriefText: 'great');
      const b = SubmitDebrief(publicId: 'm-1', debriefText: 'great');
      expect(a, b);
      expect(a.props, ['m-1', 'great']);
    });

    test('EndPlaySession supports value equality and props', () {
      const a = EndPlaySession(publicId: 'm-1', endedVia: 'completed');
      const b = EndPlaySession(publicId: 'm-1', endedVia: 'completed');
      expect(a, b);
      expect(a.props, ['m-1', 'completed']);
      expect(const EndPlaySession(publicId: 'm-1').props, [
        'm-1',
        'paused_app',
      ]);
    });

    test('SubmitRetroactiveDebrief supports value equality and props', () {
      const a = SubmitRetroactiveDebrief(
        libraryEntryPublicId: 'lib-1',
        debriefText: 'done',
      );
      const b = SubmitRetroactiveDebrief(
        libraryEntryPublicId: 'lib-1',
        debriefText: 'done',
      );
      expect(a, b);
      expect(a.props, ['lib-1', 'done']);
    });

    test('RegenerateBriefing supports value equality and props', () {
      const a = RegenerateBriefing(publicId: 'm-1', currentPosition: 'boss');
      const b = RegenerateBriefing(publicId: 'm-1', currentPosition: 'boss');
      expect(a, b);
      expect(a.props, ['m-1', 'boss']);
      expect(const RegenerateBriefing(publicId: 'm-1').props, ['m-1', null]);
    });
  });

  group('PlaySessionState', () {
    test('PlaySessionInitial supports value equality', () {
      expect(const PlaySessionInitial(), const PlaySessionInitial());
      expect(const PlaySessionInitial().props, isEmpty);
    });

    test('PlaySessionLoading supports value equality', () {
      expect(const PlaySessionLoading(), const PlaySessionLoading());
      expect(const PlaySessionLoading().props, isEmpty);
    });

    test(
      'PlaySessionListLoaded supports value equality, props and copyWith',
      () {
        final a = PlaySessionListLoaded(playSessions: [_listItem], total: 2);
        final b = PlaySessionListLoaded(playSessions: [_listItem], total: 2);
        expect(a, b);
        expect(a.isLoadingMore, false);
        expect(a.hasMore, true);
        expect(a.props, [
          [_listItem],
          2,
          false,
          null,
        ]);

        final updated = a.copyWith(isLoadingMore: true);
        expect(updated.isLoadingMore, true);
        expect(updated.playSessions, [_listItem]);
        expect(updated.total, 2);

        final errored = a.copyWith(loadMoreError: 'oops');
        expect(errored.loadMoreError, 'oops');
        expect(errored.props.last, 'oops');
      },
    );

    test('ActivePlaySessionLoaded supports value equality and props', () {
      final a = ActivePlaySessionLoaded(playSession: _playSession);
      final b = ActivePlaySessionLoaded(playSession: _playSession);
      expect(a, b);
      expect(a.props, [_playSession]);
      expect(const ActivePlaySessionLoaded().props, [null]);
    });

    test('BriefingPreviewLoaded supports value equality and props', () {
      final a = BriefingPreviewLoaded(preview: _preview, isDeep: true);
      final b = BriefingPreviewLoaded(preview: _preview, isDeep: true);
      expect(a, b);
      expect(a.props, [_preview, true]);
      expect(BriefingPreviewLoaded(preview: _preview).props, [_preview, false]);
    });

    test('DeepBriefingLoading supports value equality', () {
      expect(const DeepBriefingLoading(), const DeepBriefingLoading());
      expect(const DeepBriefingLoading().props, isEmpty);
    });

    test('PlaySessionStarted supports value equality and props', () {
      final a = PlaySessionStarted(playSession: _playSession);
      final b = PlaySessionStarted(playSession: _playSession);
      expect(a, b);
      expect(a.props, [_playSession]);
    });

    test('PlaySessionEnded supports value equality and props', () {
      final a = PlaySessionEnded(playSession: _playSession);
      final b = PlaySessionEnded(playSession: _playSession);
      expect(a, b);
      expect(a.props, [_playSession]);
    });

    test('PlaySessionError supports value equality and props', () {
      const a = PlaySessionError(message: 'boom');
      const b = PlaySessionError(message: 'boom');
      expect(a, b);
      expect(a.props, ['boom']);
    });
  });
}
