import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Shell scaffold that wraps the main authenticated pages with a
/// [BottomNavigationBar] for tab-based navigation. The Concierge tab is only
/// shown when [conciergeEnabled] (gated by a feature flag).
class ShellPage extends StatelessWidget {
  const ShellPage({
    required this.child,
    this.conciergeEnabled = false,
    super.key,
  });

  /// The current page rendered by [GoRouter] inside the shell.
  final Widget child;

  /// Whether to surface the Backlog Concierge tab.
  final bool conciergeEnabled;

  /// Ordered tab definitions, with Concierge appended last when enabled.
  List<_Tab> _tabs() {
    return [
      const _Tab(
        path: '/library',
        icon: Icons.videogame_asset,
        label: 'Library',
      ),
      const _Tab(path: '/loadout', icon: Icons.casino, label: 'Loadout'),
      const _Tab(path: '/missions', icon: Icons.flag, label: 'Missions'),
      const _Tab(path: '/analytics', icon: Icons.bar_chart, label: 'Stats'),
      if (conciergeEnabled)
        const _Tab(
          path: '/concierge',
          icon: Icons.auto_awesome,
          label: 'Concierge',
        ),
    ];
  }

  int _currentIndex(BuildContext context, List<_Tab> tabs) {
    final location = GoRouterState.of(context).matchedLocation;
    final index = tabs.indexWhere((t) => location.startsWith(t.path));
    return index < 0 ? 0 : index;
  }

  @override
  Widget build(BuildContext context) {
    final tabs = _tabs();

    return Scaffold(
      body: child,
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex(context, tabs),
        onTap: (index) => context.go(tabs[index].path),
        type: BottomNavigationBarType.fixed,
        backgroundColor: DLColors.bg,
        selectedItemColor: DLColors.coral,
        unselectedItemColor: DLColors.textDim,
        items: [
          for (final tab in tabs)
            BottomNavigationBarItem(icon: Icon(tab.icon), label: tab.label),
        ],
      ),
    );
  }
}

class _Tab {
  const _Tab({required this.path, required this.icon, required this.label});

  final String path;
  final IconData icon;
  final String label;
}
