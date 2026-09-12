import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/session_controller.dart';
import '../theme/tokens.dart';
import '../widgets/glass_card.dart';
import '../widgets/section_title.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    // Initialize session on first build
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final session = context.read<SessionController>();
      if (session.callId == null && !session.connecting) {
        session.startSession();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: PgColors.screenGradient,
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: Consumer<SessionController>(
            builder: (context, session, _) {
              return SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: PgSpace.screenH),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 20),
                    _buildHeader(session),
                    const SizedBox(height: PgSpace.section),
                    _buildProtectionCard(session),
                    const SizedBox(height: PgSpace.section),
                    _buildCallStatus(session),
                    const SizedBox(height: PgSpace.section),
                    if (session.wsConnected) _buildFactCheckWidget(session),
                    const SizedBox(height: PgSpace.section),
                    _buildActionButtons(context, session),
                    const SizedBox(height: 100),
                  ],
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(SessionController session) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'PhaseGuard',
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
                color: PgColors.white,
              ),
            ),
            _buildStatusBadge(session),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Call Protection Active',
          style: TextStyle(
            fontSize: 14,
            color: PgColors.mediumBlue,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  Widget _buildStatusBadge(SessionController session) {
    Color statusColor;
    if (session.wsConnected) {
      statusColor = PgColors.safe;
    } else if (session.connecting) {
      statusColor = PgColors.warn;
    } else {
      statusColor = PgColors.crit;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: statusColor.withValues(alpha: 0.15),
        border: Border.all(color: statusColor, width: 1.5),
        borderRadius: BorderRadius.circular(PgRadii.pill),
      ),
      child: Text(
        session.callStatusLabel,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: statusColor,
        ),
      ),
    );
  }

  Widget _buildProtectionCard(SessionController session) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Protection Status'),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildStatItem(
                label: 'Status',
                value: session.protectionActive ? 'Active' : 'Inactive',
                color: session.protectionActive ? PgColors.safe : PgColors.crit,
              ),
              _buildStatItem(
                label: 'Calls Monitored',
                value: '0',
                color: PgColors.accentBlue,
              ),
              _buildStatItem(
                label: 'Threats Blocked',
                value: '0',
                color: PgColors.crit,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem({
    required String label,
    required String value,
    required Color color,
  }) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(
            fontSize: 11,
            color: PgColors.mediumBlue,
          ),
        ),
      ],
    );
  }

  Widget _buildCallStatus(SessionController session) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Current Call'),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Call ID',
                    style: const TextStyle(
                      fontSize: 11,
                      color: PgColors.mediumBlue,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    session.callId?.substring(0, 12) ?? 'None',
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: PgColors.white,
                      fontFamily: 'Courier',
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: PgColors.accentBlue.withValues(alpha: 0.2),
                  border: Border.all(
                    color: PgColors.accentBlue,
                    width: 1,
                  ),
                  borderRadius: BorderRadius.circular(PgRadii.bar),
                ),
                child: Text(
                  session.callTag,
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: PgColors.accentBlue,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _buildRiskGauge(session),
        ],
      ),
    );
  }

  Widget _buildRiskGauge(SessionController session) {
    final riskState = session.riskState;
    Color riskColor;
    switch (session.factcheck?.status) {
      case 'SAFE':
        riskColor = PgColors.safe;
        break;
      case 'CRITICAL':
        riskColor = PgColors.crit;
        break;
      case 'WARNING':
      case 'UNCERTAIN':
        riskColor = PgColors.warn;
        break;
      default:
        riskColor = PgColors.mediumBlue;
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Risk Level',
              style: const TextStyle(
                fontSize: 11,
                color: PgColors.mediumBlue,
              ),
            ),
            Text(
              riskState,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: riskColor,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: session.gaugeDegrees / 90,
            minHeight: 6,
            backgroundColor: PgColors.glassBgStrong,
            valueColor: AlwaysStoppedAnimation(riskColor),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          session.riskNote,
          style: const TextStyle(
            fontSize: 10,
            color: PgColors.mediumBlue,
            height: 1.4,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }

  Widget _buildFactCheckWidget(SessionController session) {
    final fc = session.factcheck;
    if (fc == null) return const SizedBox.shrink();

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Latest Fact Check'),
          const SizedBox(height: 12),
          Text(
            fc.message,
            style: const TextStyle(
              fontSize: 12,
              color: PgColors.lightBlue,
              height: 1.5,
            ),
          ),
          if (fc.evidenceUrls.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              'Evidence: ${fc.evidenceUrls.length} source(s)',
              style: const TextStyle(
                fontSize: 10,
                color: PgColors.mediumBlue,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildActionButtons(BuildContext context, SessionController session) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SectionTitle('Actions'),
        const SizedBox(height: 12),
        if (!session.wsConnected)
          ElevatedButton.icon(
            onPressed: session.connecting
                ? null
                : () {
                    session.startSession();
                  },
            icon: const Icon(Icons.play_arrow),
            label: Text(session.connecting ? 'Connecting...' : 'Start Session'),
            style: ElevatedButton.styleFrom(
              backgroundColor: PgColors.accentBlue,
              foregroundColor: PgColors.white,
              padding: const EdgeInsets.symmetric(vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(PgRadii.bar),
              ),
            ),
          )
        else ...[
          _buildActionButton(
            onPressed: () {
              _showBlockReportDialog(context, session);
            },
            label: 'Block & Report',
            icon: Icons.block,
            color: PgColors.crit,
          ),
          const SizedBox(height: 8),
          _buildActionButton(
            onPressed: () {
              session.continueMonitoring();
            },
            label: 'Continue Monitoring',
            icon: Icons.visibility,
            color: PgColors.accentBlue,
          ),
        ],
        if (session.error != null) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: PgColors.crit.withValues(alpha: 0.1),
              border: Border.all(color: PgColors.crit, width: 1),
              borderRadius: BorderRadius.circular(PgRadii.bar),
            ),
            child: Text(
              'Error: ${session.error}',
              style: const TextStyle(
                fontSize: 11,
                color: PgColors.crit,
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildActionButton({
    required VoidCallback onPressed,
    required String label,
    required IconData icon,
    required Color color,
  }) {
    return ElevatedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: color.withValues(alpha: 0.15),
        foregroundColor: color,
        side: BorderSide(color: color, width: 1.5),
        padding: const EdgeInsets.symmetric(vertical: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(PgRadii.bar),
        ),
      ),
    );
  }

  void _showBlockReportDialog(BuildContext context, SessionController session) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: PgColors.bgSecondary,
        title: const Text(
          'Block & Report',
          style: TextStyle(color: PgColors.white),
        ),
        content: const Text(
          'This will escalate and block the current call. Continue?',
          style: TextStyle(color: PgColors.lightBlue),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);
              try {
                final draft = await session.draftBlockAndReport();
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Escalation ready: ${draft.draftId}'),
                      backgroundColor: PgColors.safe,
                    ),
                  );
                }
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Error: $e'),
                      backgroundColor: PgColors.crit,
                    ),
                  );
                }
              }
            },
            child: const Text(
              'Confirm',
              style: TextStyle(color: PgColors.crit),
            ),
          ),
        ],
      ),
    );
  }
}
