import 'package:app/core/config/feature_flags.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('FeatureFlags', () {
    test('default constructor disables backlogLetMeCarry', () {
      const flags = FeatureFlags();
      expect(flags.backlogLetMeCarry, false);
    });

    test('explicit constructor enables backlogLetMeCarry', () {
      const flags = FeatureFlags(backlogLetMeCarry: true);
      expect(flags.backlogLetMeCarry, true);
    });

    test('fromEnv reads ENABLE_LET_ME_CARRY=true as enabled', () {
      dotenv.testLoad(fileInput: 'ENABLE_LET_ME_CARRY=true');
      final flags = FeatureFlags.fromEnv();
      expect(flags.backlogLetMeCarry, true);
    });

    test('fromEnv treats non-true value as disabled', () {
      dotenv.testLoad(fileInput: 'ENABLE_LET_ME_CARRY=yes');
      final flags = FeatureFlags.fromEnv();
      expect(flags.backlogLetMeCarry, false);
    });

    test('fromEnv defaults to disabled when key is missing', () {
      dotenv.testLoad();
      final flags = FeatureFlags.fromEnv();
      expect(flags.backlogLetMeCarry, false);
    });
  });
}
