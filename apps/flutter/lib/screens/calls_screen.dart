import 'package:flutter/material.dart';

import '../theme/tokens.dart';
import '../widgets/glass_card.dart';
import '../widgets/section_title.dart';

class CallsScreen extends StatefulWidget {
  const CallsScreen({super.key});

  @override
  State<CallsScreen> createState() => _CallsScreenState();
}

class _CallsScreenState extends State<CallsScreen> {
  late List<CallRecord> calls;

  @override
  void initState() {
    super.initState();
    calls = [
      CallRecord(
        id: '1',
        caller: 'Unknown Number +91-XXXX123456',
        time: '2 hours ago',
        duration: '2:34',
        riskLevel: 'high',
        status: 'blocked',
      ),
      CallRecord(
        id: '2',
        caller: 'Bank Customer Service',
        time: '5 hours ago',
        duration: '5:12',
        riskLevel: 'low',
        status: 'safe',
      ),
      CallRecord(
        id: '3',
        caller: 'Government Portal',
        time: '1 day ago',
        duration: '3:45',
        riskLevel: 'high',
        status: 'monitored',
      ),
    ];
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
        child: const SafeArea(
          child: SingleChildScrollView(
            padding: EdgeInsets.symmetric(horizontal: PgSpace.screenH),
            child: _CallsListView(),
          ),
        ),
      ),
    );
  }
}

class _CallsListView extends StatefulWidget {
  const _CallsListView();

  @override
  State<_CallsListView> createState() => _CallsListViewState();
}

class _CallsListViewState extends State<_CallsListView> {
  late List<CallRecord> calls;

  @override
  void initState() {
    super.initState();
    calls = [
      CallRecord(
        id: '1',
        caller: 'Unknown Number +91-XXXX123456',
        time: '2 hours ago',
        duration: '2:34',
        riskLevel: 'high',
        status: 'blocked',
      ),
      CallRecord(
        id: '2',
        caller: 'Bank Customer Service',
        time: '5 hours ago',
        duration: '5:12',
        riskLevel: 'low',
        status: 'safe',
      ),
      CallRecord(
        id: '3',
        caller: 'Government Portal',
        time: '1 day ago',
        duration: '3:45',
        riskLevel: 'high',
        status: 'monitored',
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 20),
        const SectionTitle('Call History'),
        const SizedBox(height: PgSpace.section),
        ...calls.map((call) => _buildCallItem(call)),
        const SizedBox(height: 100),
      ],
    );
  }

  Widget _buildCallItem(CallRecord call) {
    final riskColor = _getRiskColor(call.riskLevel);
    final statusLabel = _getStatusLabel(call.status);

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GlassCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        call.caller,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: PgColors.white,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${call.time} • ${call.duration}',
                        style: const TextStyle(
                          fontSize: 11,
                          color: PgColors.mediumBlue,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: riskColor.withValues(alpha: 0.15),
                    border: Border.all(color: riskColor, width: 1),
                    borderRadius: BorderRadius.circular(PgRadii.bar),
                  ),
                  child: Text(
                    call.riskLevel.toUpperCase(),
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: riskColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: riskColor,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  statusLabel,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: PgColors.lightBlue,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _getRiskColor(String level) {
    switch (level) {
      case 'low':
        return PgColors.safe;
      case 'medium':
        return PgColors.warn;
      case 'high':
        return PgColors.crit;
      default:
        return PgColors.mediumBlue;
    }
  }

  String _getStatusLabel(String status) {
    switch (status) {
      case 'blocked':
        return 'Blocked & Reported';
      case 'safe':
        return 'Safe Call';
      case 'monitored':
        return 'Monitored';
      default:
        return 'Unknown';
    }
  }
}

class CallRecord {
  final String id;
  final String caller;
  final String time;
  final String duration;
  final String riskLevel;
  final String status;

  CallRecord({
    required this.id,
    required this.caller,
    required this.time,
    required this.duration,
    required this.riskLevel,
    required this.status,
  });
}
