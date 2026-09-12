/// WebSocket payloads the FastAPI call socket actually emits.
class FactCheckUpdate {
  FactCheckUpdate({
    required this.status,
    required this.message,
    required this.ts,
    this.evidenceUrls = const [],
    this.category,
  });

  final String status; // SAFE | CRITICAL | UNCERTAIN | VERIFYING | WARNING
  final String message;
  final List<String> evidenceUrls;
  final String ts;
  final String? category;

  factory FactCheckUpdate.fromJson(Map<String, dynamic> json) {
    final urls = json['evidence_urls'];
    return FactCheckUpdate(
      status: (json['status'] as String? ?? '').toUpperCase(),
      message: json['message'] as String? ?? '',
      ts: json['ts'] as String? ?? '',
      category: json['category'] as String?,
      evidenceUrls: urls is List
          ? urls.map((e) => e.toString()).toList()
          : const [],
    );
  }
}

class EnsembleUpdate {
  EnsembleUpdate({
    required this.label,
    required this.ensembleScore,
    required this.ts,
    this.reason,
  });

  final String label;
  final double ensembleScore;
  final String ts;
  final String? reason;

  factory EnsembleUpdate.fromJson(Map<String, dynamic> json) {
    return EnsembleUpdate(
      label: json['label'] as String? ?? '',
      ensembleScore: (json['ensemble_score'] as num?)?.toDouble() ?? 0,
      ts: json['ts'] as String? ?? '',
      reason: json['reason'] as String?,
    );
  }
}

class CallInitResult {
  CallInitResult({
    required this.callId,
    required this.token,
    required this.wsUrl,
    required this.expiresInSeconds,
  });

  final String callId;
  final String token;
  final String wsUrl;
  final int expiresInSeconds;

  factory CallInitResult.fromJson(Map<String, dynamic> json) {
    return CallInitResult(
      callId: json['call_id'] as String,
      token: json['token'] as String,
      wsUrl: json['ws_url'] as String? ?? '',
      expiresInSeconds: json['expires_in_seconds'] as int? ?? 0,
    );
  }
}

class EscalationDraft {
  EscalationDraft({
    required this.draftId,
    required this.payloadSummary,
    required this.destination,
    required this.verdict,
    required this.warning,
  });

  final String draftId;
  final String payloadSummary;
  final String destination;
  final String verdict;
  final String warning;

  factory EscalationDraft.fromJson(Map<String, dynamic> json) {
    return EscalationDraft(
      draftId: json['draft_id'] as String,
      payloadSummary: json['payload_summary'] as String? ?? '',
      destination: json['destination'] as String? ?? '',
      verdict: json['verdict'] as String? ?? '',
      warning: json['warning'] as String? ?? '',
    );
  }
}

class CallStatus {
  CallStatus({
    required this.callId,
    required this.state,
    this.ensembleLabel,
    this.factcheckCount = 0,
    this.latestVerdict,
  });

  final String callId;
  final String state;
  final String? ensembleLabel;
  final int factcheckCount;
  final FactCheckUpdate? latestVerdict;

  factory CallStatus.fromJson(Map<String, dynamic> json) {
    final verdict = json['latest_verdict'];
    return CallStatus(
      callId: json['call_id'] as String? ?? '',
      state: json['state'] as String? ?? '',
      ensembleLabel: json['ensemble_label'] as String?,
      factcheckCount: json['factcheck_count'] as int? ?? 0,
      latestVerdict: verdict is Map<String, dynamic>
          ? FactCheckUpdate.fromJson(verdict)
          : null,
    );
  }
}
