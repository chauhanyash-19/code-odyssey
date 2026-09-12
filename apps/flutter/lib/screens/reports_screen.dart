import 'package:flutter/material.dart';

import '../theme/tokens.dart';
import '../widgets/glass_card.dart';
import '../widgets/section_title.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  late List<ReportItem> reports;

  @override
  void initState() {
    super.initState();
    reports = [
      ReportItem(
        id: '1',
        type: 'Banking Fraud',
        callerId: '+91-XXXX123456',
        timestamp: '2 hours ago',
        status: 'submitted',
      ),
      ReportItem(
        id: '2',
        type: 'Tech Support Scam',
        callerId: '+1-888-XXXXX',
        timestamp: '1 day ago',
        status: 'investigating',
      ),
      ReportItem(
        id: '3',
        type: 'Government Impersonation',
        callerId: '+91-XXXX789012',
        timestamp: '3 days ago',
        status: 'resolved',
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
            child: _ReportsListView(),
          ),
        ),
      ),
    );
  }
}

class _ReportsListView extends StatefulWidget {
  const _ReportsListView();

  @override
  State<_ReportsListView> createState() => _ReportsListViewState();
}

class _ReportsListViewState extends State<_ReportsListView> {
  late List<ReportItem> reports;

  @override
  void initState() {
    super.initState();
    reports = [
      ReportItem(
        id: '1',
        type: 'Banking Fraud',
        callerId: '+91-XXXX123456',
        timestamp: '2 hours ago',
        status: 'submitted',
      ),
      ReportItem(
        id: '2',
        type: 'Tech Support Scam',
        callerId: '+1-888-XXXXX',
        timestamp: '1 day ago',
        status: 'investigating',
      ),
      ReportItem(
        id: '3',
        type: 'Government Impersonation',
        callerId: '+91-XXXX789012',
        timestamp: '3 days ago',
        status: 'resolved',
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 20),
        const SectionTitle('Reports'),
        const SizedBox(height: PgSpace.section),
        ...reports.map((report) => _buildReportItem(report)),
        const SizedBox(height: 100),
      ],
    );
  }

  Widget _buildReportItem(ReportItem report) {
    final statusColor = _getStatusColor(report.status);
    final statusLabel = _getStatusLabel(report.status);

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
                        report.type,
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
                        report.callerId,
                        style: const TextStyle(
                          fontSize: 11,
                          color: PgColors.mediumBlue,
                          fontFamily: 'Courier',
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.15),
                    border: Border.all(color: statusColor, width: 1),
                    borderRadius: BorderRadius.circular(PgRadii.bar),
                  ),
                  child: Text(
                    statusLabel,
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: statusColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              report.timestamp,
              style: const TextStyle(
                fontSize: 11,
                color: PgColors.mediumBlue,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'submitted':
        return PgColors.warn;
      case 'investigating':
        return PgColors.accentBlue;
      case 'resolved':
        return PgColors.safe;
      default:
        return PgColors.mediumBlue;
    }
  }

  String _getStatusLabel(String status) {
    switch (status) {
      case 'submitted':
        return 'Submitted';
      case 'investigating':
        return 'Investigating';
      case 'resolved':
        return 'Resolved';
      default:
        return 'Unknown';
    }
  }
}

class ReportItem {
  final String id;
  final String type;
  final String callerId;
  final String timestamp;
  final String status;

  ReportItem({
    required this.id,
    required this.type,
    required this.callerId,
    required this.timestamp,
    required this.status,
  });
}
