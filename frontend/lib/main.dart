import 'package:flutter/material.dart';

void main() => runApp(const ExamAdminApp());

class ExamAdminApp extends StatefulWidget {
  const ExamAdminApp({super.key});
  @override
  State<ExamAdminApp> createState() => _ExamAdminAppState();
}

class _ExamAdminAppState extends State<ExamAdminApp> {
  ThemeMode _themeMode = ThemeMode.light;
  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'ExamOS Admin',
    themeMode: _themeMode,
    theme: appTheme(Brightness.light),
    darkTheme: appTheme(Brightness.dark),
    home: AdminShell(
      onThemeChanged: () => setState(
        () => _themeMode = _themeMode == ThemeMode.dark
            ? ThemeMode.light
            : ThemeMode.dark,
      ),
    ),
  );
}

ThemeData appTheme(Brightness brightness) {
  final scheme = ColorScheme.fromSeed(
    seedColor: const Color(0xFF6256E8),
    brightness: brightness,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: brightness == Brightness.light
        ? const Color(0xFFF7F7FC)
        : const Color(0xFF12121A),
    cardTheme: CardThemeData(
      elevation: 0,
      color: brightness == Brightness.light
          ? Colors.white
          : const Color(0xFF20202B),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: scheme.surfaceContainerHighest.withValues(alpha: .45),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide.none,
      ),
    ),
  );
}

class NavItem {
  const NavItem(this.label, this.icon, {this.group = 'Management'});
  final String label, group;
  final IconData icon;
}

const navItems = [
  NavItem('Dashboard', Icons.grid_view_rounded, group: 'Overview'),
  NavItem('Users', Icons.people_alt_outlined),
  NavItem('Question Bank', Icons.quiz_outlined),
  NavItem('Subjects', Icons.auto_stories_outlined),
  NavItem('Chapters', Icons.account_tree_outlined),
  NavItem('Topics', Icons.topic_outlined),
  NavItem('Tests', Icons.assignment_outlined),
  NavItem('Test Series', Icons.layers_outlined),
  NavItem('Current Affairs', Icons.newspaper_outlined),
  NavItem('Study Materials', Icons.folder_copy_outlined),
  NavItem('Leaderboard', Icons.emoji_events_outlined, group: 'Engagement'),
  NavItem('Subscriptions', Icons.workspace_premium_outlined),
  NavItem('Payments', Icons.payments_outlined),
  NavItem('Coupons', Icons.confirmation_number_outlined),
  NavItem('Notifications', Icons.notifications_outlined),
  NavItem('Reports', Icons.assessment_outlined),
  NavItem('Support', Icons.support_agent_outlined),
  NavItem('Feedback', Icons.rate_review_outlined),
  NavItem('Banner Management', Icons.photo_library_outlined, group: 'Content'),
  NavItem('Offers', Icons.local_offer_outlined),
  NavItem('Books', Icons.menu_book_outlined),
  NavItem('Audit Logs', Icons.history_outlined, group: 'Administration'),
  NavItem('Roles', Icons.admin_panel_settings_outlined),
  NavItem('Settings', Icons.settings_outlined),
  NavItem('Profile', Icons.person_outline),
];

class AdminShell extends StatefulWidget {
  const AdminShell({super.key, required this.onThemeChanged});
  final VoidCallback onThemeChanged;
  @override
  State<AdminShell> createState() => _AdminShellState();
}

class _AdminShellState extends State<AdminShell> {
  int selected = 0;
  bool compact = false;
  @override
  Widget build(BuildContext context) {
    final desktop = MediaQuery.sizeOf(context).width >= 1024;
    return Scaffold(
      drawer: desktop
          ? null
          : Drawer(
              child: _Navigation(
                selected: selected,
                onSelect: _select,
                compact: false,
              ),
            ),
      body: Row(
        children: [
          if (desktop)
            AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: compact ? 82 : 254,
              child: _Navigation(
                selected: selected,
                onSelect: _select,
                compact: compact,
              ),
            ),
          Expanded(
            child: Column(
              children: [
                _TopBar(
                  title: navItems[selected].label,
                  onMenu: desktop
                      ? () => setState(() => compact = !compact)
                      : () => Scaffold.of(context).openDrawer(),
                  onTheme: widget.onThemeChanged,
                ),
                Expanded(child: _PageBody(page: navItems[selected].label)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _select(int value) {
    setState(() => selected = value);
    if (Navigator.canPop(context)) Navigator.pop(context);
  }
}

class _Navigation extends StatelessWidget {
  const _Navigation({
    required this.selected,
    required this.onSelect,
    required this.compact,
  });
  final int selected;
  final ValueChanged<int> onSelect;
  final bool compact;
  @override
  Widget build(BuildContext context) {
    String? lastGroup;
    final scheme = Theme.of(context).colorScheme;
    return ColoredBox(
      color: scheme.surface,
      child: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: EdgeInsets.fromLTRB(compact ? 18 : 22, 18, 14, 16),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF6256E8), Color(0xFF9B70FF)],
                      ),
                      borderRadius: BorderRadius.circular(13),
                    ),
                    child: const Icon(
                      Icons.school_rounded,
                      color: Colors.white,
                    ),
                  ),
                  if (!compact)
                    const Padding(
                      padding: EdgeInsets.only(left: 11),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'ExamOS',
                            style: TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 18,
                            ),
                          ),
                          Text(
                            'ADMIN CONSOLE',
                            style: TextStyle(fontSize: 9, letterSpacing: 1.2),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                children: [
                  for (var i = 0; i < navItems.length; i++) ...[
                    if (navItems[i].group != lastGroup)
                      Builder(
                        builder: (_) {
                          lastGroup = navItems[i].group;
                          return compact
                              ? const SizedBox(height: 12)
                              : Padding(
                                  padding: const EdgeInsets.fromLTRB(
                                    12,
                                    17,
                                    0,
                                    7,
                                  ),
                                  child: Text(
                                    lastGroup!.toUpperCase(),
                                    style: TextStyle(
                                      color: scheme.outline,
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                      letterSpacing: 1,
                                    ),
                                  ),
                                );
                        },
                      ),
                    Tooltip(
                      message: compact ? navItems[i].label : '',
                      child: ListTile(
                        leading: Icon(navItems[i].icon, size: 21),
                        title: compact ? null : Text(navItems[i].label),
                        selected: selected == i,
                        selectedTileColor: scheme.primaryContainer,
                        selectedColor: scheme.primary,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(11),
                        ),
                        contentPadding: EdgeInsets.symmetric(
                          horizontal: compact ? 18 : 12,
                        ),
                        onTap: () => onSelect(i),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            if (!compact)
              Container(
                margin: const EdgeInsets.all(14),
                padding: const EdgeInsets.all(13),
                decoration: BoxDecoration(
                  color: scheme.primaryContainer,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.verified_user_outlined),
                    SizedBox(width: 9),
                    Expanded(
                      child: Text(
                        'System healthy\nAll services operational',
                        style: TextStyle(fontSize: 11),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.title,
    required this.onMenu,
    required this.onTheme,
  });
  final String title;
  final VoidCallback onMenu, onTheme;
  @override
  Widget build(BuildContext context) => Container(
    height: 78,
    padding: const EdgeInsets.symmetric(horizontal: 24),
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.surface,
      border: Border(
        bottom: BorderSide(
          color: Theme.of(context).dividerColor.withValues(alpha: .45),
        ),
      ),
    ),
    child: Row(
      children: [
        IconButton(onPressed: onMenu, icon: const Icon(Icons.menu_rounded)),
        const SizedBox(width: 10),
        Text(
          title,
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
        ),
        const Spacer(),
        SizedBox(
          width: 260,
          child: TextField(
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Search users, tests, questions...',
              isDense: true,
            ),
          ),
        ),
        const SizedBox(width: 12),
        IconButton(
          onPressed: onTheme,
          icon: const Icon(Icons.dark_mode_outlined),
        ),
        Badge(
          label: const Text('3'),
          child: IconButton(
            onPressed: () => _info(
              context,
              'Notifications',
              '3 moderation actions require attention.',
            ),
            icon: const Icon(Icons.notifications_none_rounded),
          ),
        ),
        const SizedBox(width: 8),
        const CircleAvatar(radius: 18, child: Text('RA')),
      ],
    ),
  );
}

class _PageBody extends StatelessWidget {
  const _PageBody({required this.page});
  final String page;
  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    padding: const EdgeInsets.all(24),
    child: page == 'Dashboard'
        ? const DashboardPage()
        : ManagementPage(title: page),
  );
}

class DashboardPage extends StatelessWidget {
  const DashboardPage({super.key});
  @override
  Widget build(BuildContext context) {
    final cards = [
      (
        'Today’s Revenue',
        '₹1,84,250',
        '+18.2%',
        Icons.account_balance_wallet_outlined,
      ),
      ('Total Users', '2,48,690', '+12.4%', Icons.people_outline),
      ('Premium Users', '38,429', '+8.7%', Icons.workspace_premium_outlined),
      ('Active Now', '1,284', '+4.1%', Icons.bolt_outlined),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Good morning, Reepa 👋',
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 5),
                  Text(
                    'Here is what is happening with your exam platform today.',
                  ),
                ],
              ),
            ),
            FilledButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.add),
              label: const Text('Create Test'),
            ),
          ],
        ),
        const SizedBox(height: 22),
        LayoutBuilder(
          builder: (context, c) => Wrap(
            spacing: 16,
            runSpacing: 16,
            children: cards
                .map(
                  (e) => SizedBox(
                    width: c.maxWidth > 900
                        ? (c.maxWidth - 48) / 4
                        : c.maxWidth > 550
                        ? (c.maxWidth - 16) / 2
                        : c.maxWidth,
                    child: MetricCard(
                      label: e.$1,
                      value: e.$2,
                      growth: e.$3,
                      icon: e.$4,
                    ),
                  ),
                )
                .toList(),
          ),
        ),
        const SizedBox(height: 20),
        LayoutBuilder(
          builder: (context, c) => c.maxWidth > 850
              ? const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 7, child: RevenueChart()),
                    SizedBox(width: 20),
                    Expanded(flex: 4, child: ActivityPanel()),
                  ],
                )
              : const Column(
                  children: [
                    RevenueChart(),
                    SizedBox(height: 20),
                    ActivityPanel(),
                  ],
                ),
        ),
        const SizedBox(height: 20),
        LayoutBuilder(
          builder: (context, c) => c.maxWidth > 850
              ? const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: PerformancePanel()),
                    SizedBox(width: 20),
                    Expanded(child: PendingPanel()),
                  ],
                )
              : const Column(
                  children: [
                    PerformancePanel(),
                    SizedBox(height: 20),
                    PendingPanel(),
                  ],
                ),
        ),
      ],
    );
  }
}

class MetricCard extends StatelessWidget {
  const MetricCard({
    super.key,
    required this.label,
    required this.value,
    required this.growth,
    required this.icon,
  });
  final String label, value, growth;
  final IconData icon;
  @override
  Widget build(BuildContext context) {
    final s = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(9),
                  decoration: BoxDecoration(
                    color: s.primaryContainer,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, color: s.primary),
                ),
                const Spacer(),
                Text(
                  growth,
                  style: const TextStyle(
                    color: Color(0xFF159B62),
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 17),
            Text(
              value,
              style: const TextStyle(fontSize: 25, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(color: s.onSurfaceVariant, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }
}

class RevenueChart extends StatelessWidget {
  const RevenueChart({super.key});
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Expanded(
                child: Text(
                  'Revenue Overview',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
                ),
              ),
              Text('Last 30 days'),
            ],
          ),
          const SizedBox(height: 24),
          SizedBox(
            height: 210,
            child: CustomPaint(
              painter: ChartPainter(Theme.of(context).colorScheme.primary),
              child: const SizedBox.expand(),
            ),
          ),
          const Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              Text('Jul 01'),
              Text('Jul 08'),
              Text('Jul 15'),
              Text('Jul 22'),
              Text('Today'),
            ],
          ),
        ],
      ),
    ),
  );
}

class ChartPainter extends CustomPainter {
  ChartPainter(this.color);
  final Color color;
  @override
  void paint(Canvas c, Size s) {
    final grid = Paint()
      ..color = const Color(0xFFE7E7EF)
      ..strokeWidth = 1;
    for (var i = 0; i < 5; i++)
      c.drawLine(
        Offset(0, i * s.height / 4),
        Offset(s.width, i * s.height / 4),
        grid,
      );
    final path = Path()
      ..moveTo(0, s.height * .77)
      ..cubicTo(
        s.width * .15,
        s.height * .7,
        s.width * .17,
        s.height * .48,
        s.width * .29,
        s.height * .59,
      )
      ..cubicTo(
        s.width * .42,
        s.height * .72,
        s.width * .49,
        s.height * .27,
        s.width * .62,
        s.height * .43,
      )
      ..cubicTo(
        s.width * .74,
        s.height * .54,
        s.width * .83,
        s.height * .17,
        s.width,
        s.height * .09,
      );
    c.drawPath(
      path,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(covariant ChartPainter old) => old.color != color;
}

class ActivityPanel extends StatelessWidget {
  const ActivityPanel({super.key});
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Recent Activity',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
          ),
          const SizedBox(height: 12),
          ...[
            'Question #TN-1042 approved by Karthik',
            'Premium plan purchased by Priya S.',
            'Group 4 Grand Test published',
            '21 new support tickets received',
          ].asMap().entries.map(
            (e) => ListTile(
              contentPadding: EdgeInsets.zero,
              leading: CircleAvatar(
                radius: 17,
                child: Icon(
                  [
                    Icons.check,
                    Icons.payments,
                    Icons.rocket_launch,
                    Icons.support,
                  ][e.key],
                  size: 17,
                ),
              ),
              title: Text(e.value, style: const TextStyle(fontSize: 13)),
              subtitle: Text('${e.key + 1}h ago'),
            ),
          ),
          TextButton(onPressed: () {}, child: const Text('View all activity')),
        ],
      ),
    ),
  );
}

class PerformancePanel extends StatelessWidget {
  const PerformancePanel({super.key});
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Top Subjects',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
          ),
          const SizedBox(height: 16),
          ...const [
            ('General Tamil', .86, '86%'),
            ('General Studies', .72, '72%'),
            ('Aptitude', .64, '64%'),
            ('Current Affairs', .51, '51%'),
          ].map(
            (r) => Padding(
              padding: const EdgeInsets.only(bottom: 15),
              child: Row(
                children: [
                  SizedBox(width: 120, child: Text(r.$1)),
                  Expanded(
                    child: LinearProgressIndicator(
                      value: r.$2,
                      minHeight: 9,
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(r.$3),
                ],
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class PendingPanel extends StatelessWidget {
  const PendingPanel({super.key});
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Needs Attention',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
          ),
          const SizedBox(height: 10),
          ...const [
            ('Question approval queue', '128 pending', Icons.quiz_outlined),
            ('Content reviews', '24 pending', Icons.fact_check_outlined),
            ('Failed payments', '8 to review', Icons.error_outline),
            ('Support tickets', '21 open', Icons.headset_mic_outlined),
          ].map(
            (e) => ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(e.$3),
              title: Text(e.$1),
              trailing: Text(
                e.$2,
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class ManagementPage extends StatefulWidget {
  const ManagementPage({super.key, required this.title});
  final String title;
  @override
  State<ManagementPage> createState() => _ManagementPageState();
}

class _ManagementPageState extends State<ManagementPage> {
  String query = '';
  int page = 0;
  @override
  Widget build(BuildContext context) {
    final records = _records
        .where(
          (e) =>
              e.$1.toLowerCase().contains(query.toLowerCase()) ||
              e.$2.toLowerCase().contains(query.toLowerCase()),
        )
        .toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.title,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 24,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Manage ${widget.title.toLowerCase()} with roles, filters and audit-ready actions.',
                  ),
                ],
              ),
            ),
            FilledButton.icon(
              onPressed: () => _editor(context, widget.title),
              icon: const Icon(Icons.add),
              label: Text('Add ${_singular(widget.title)}'),
            ),
          ],
        ),
        const SizedBox(height: 22),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              children: [
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    SizedBox(
                      width: 280,
                      child: TextField(
                        onChanged: (v) => setState(() => query = v),
                        decoration: const InputDecoration(
                          prefixIcon: Icon(Icons.search),
                          hintText: 'Search records',
                        ),
                      ),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => _filter(context),
                      icon: const Icon(Icons.filter_list),
                      label: const Text('Advanced filters'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => _info(
                        context,
                        'Export started',
                        'Your CSV export will be available in the Reports center.',
                      ),
                      icon: const Icon(Icons.file_download_outlined),
                      label: const Text('Export'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => _info(
                        context,
                        'Import records',
                        'Excel, CSV and JSON import is ready for API integration.',
                      ),
                      icon: const Icon(Icons.file_upload_outlined),
                      label: const Text('Import'),
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                _DataTable(
                  rows: records,
                  title: widget.title,
                  page: page,
                  onPage: (v) => setState(() => page = v),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _Spare {}

const _records = [
  ('TNPSC Group 4 – Grand Mock #12', 'Published', '24 Jul 2026'),
  ('General Tamil: Unit 4', 'Pending review', '23 Jul 2026'),
  ('Priyadarshini Rajendran', 'Active', '23 Jul 2026'),
  ('Indian Polity Question Set', 'Approved', '22 Jul 2026'),
  ('July Current Affairs', 'Draft', '21 Jul 2026'),
  ('Group 2A Premium Plan', 'Active', '20 Jul 2026'),
];

class _DataTable extends StatelessWidget {
  const _DataTable({
    required this.rows,
    required this.title,
    required this.page,
    required this.onPage,
  });
  final List<(String, String, String)> rows;
  final String title;
  final int page;
  final ValueChanged<int> onPage;
  @override
  Widget build(BuildContext context) {
    final approved = <String>{'Active', 'Published', 'Approved'};
    return Column(
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            columns: const [
              DataColumn(label: Text('NAME')),
              DataColumn(label: Text('STATUS')),
              DataColumn(label: Text('UPDATED')),
              DataColumn(label: Text('ACTIONS')),
            ],
            rows: rows.map((r) {
              final good = approved.contains(r.$2);
              final color = good ? Colors.green : Colors.orange;
              return DataRow(
                cells: [
                  DataCell(Text(r.$1)),
                  DataCell(
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 9,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: .12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        r.$2,
                        style: TextStyle(color: color, fontSize: 12),
                      ),
                    ),
                  ),
                  DataCell(Text(r.$3)),
                  DataCell(
                    Row(
                      children: [
                        IconButton(
                          onPressed: () => _editor(context, title),
                          icon: const Icon(Icons.edit_outlined, size: 19),
                        ),
                        IconButton(
                          onPressed: () => _info(
                            context,
                            'Record actions',
                            'Version history, visibility controls, audit logs, and deletion safeguards are available here.',
                          ),
                          icon: const Icon(Icons.more_horiz, size: 19),
                        ),
                      ],
                    ),
                  ),
                ],
              );
            }).toList(),
          ),
        ),
        const Divider(),
        Row(
          children: [
            Text('${rows.length} records'),
            const Spacer(),
            IconButton(
              onPressed: page > 0 ? () => onPage(page - 1) : null,
              icon: const Icon(Icons.chevron_left),
            ),
            Text('Page ${page + 1}'),
            IconButton(
              onPressed: () => onPage(page + 1),
              icon: const Icon(Icons.chevron_right),
            ),
          ],
        ),
      ],
    );
  }
}

String _singular(String name) =>
    name.endsWith('s') ? name.substring(0, name.length - 1) : name;
void _editor(BuildContext context, String label) {
  showDialog(
    context: context,
    builder: (context) => AlertDialog(
      title: Text('${_singular(label)} editor'),
      content: SizedBox(
        width: 480,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              decoration: InputDecoration(
                labelText: '${_singular(label)} name',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Description / instructions',
              ),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField(
              items: const [
                DropdownMenuItem(value: 'Draft', child: Text('Draft')),
                DropdownMenuItem(value: 'Published', child: Text('Published')),
              ],
              onChanged: (_) {},
              decoration: const InputDecoration(labelText: 'Status'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Save draft'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Publish'),
        ),
      ],
    ),
  );
}

void _filter(BuildContext context) {
  showModalBottomSheet(
    context: context,
    showDragHandle: true,
    builder: (context) => Padding(
      padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Advanced filters',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 20),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SizedBox(
                width: 180,
                child: DropdownButtonFormField(
                  items: const [
                    DropdownMenuItem(value: 'All', child: Text('All statuses')),
                  ],
                  onChanged: (_) {},
                  decoration: const InputDecoration(labelText: 'Status'),
                ),
              ),
              SizedBox(
                width: 180,
                child: TextField(
                  decoration: const InputDecoration(labelText: 'Date range'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Align(
            alignment: Alignment.centerRight,
            child: FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Apply filters'),
            ),
          ),
        ],
      ),
    ),
  );
}

void _info(BuildContext context, String title, String message) => showDialog(
  context: context,
  builder: (c) => AlertDialog(
    title: Text(title),
    content: Text(message),
    actions: [
      TextButton(onPressed: () => Navigator.pop(c), child: const Text('Close')),
    ],
  ),
);
