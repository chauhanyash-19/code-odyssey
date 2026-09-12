import 'dart:async';
import 'package:flutter/foundation.dart';

import '../models/protocol.dart';
import '../services/api_client.dart';
import '../services/call_socket.dart';

class SessionController extends ChangeNotifier {
  SessionController({ApiClient? api, CallSocket? socket})
      : _api = api ?? ApiClient(),
        _socket = socket ?? CallSocket();

  final ApiClient _api;
  final CallSocket _socket;

  bool connecting = false;
  bool wsConnected = false;
  String? error;
  String? callId;
  String? token;

  FactCheckUpdate? factcheck;
  EnsembleUpdate? ensemble;
  bool dspEnabled = false;
  String? lastActionMessage;

  Timer? _healthCheckTimer;
  static const _healthCheckInterval = Duration(minutes: 10); // Check health every 10 minutes

  bool get protectionActive => wsConnected;

  String get callStatusLabel {
    if (connecting) return 'Connecting';
    if (wsConnected) return 'Live';
    return 'Offline';
  }

  String get authenticityLabel {
    final e = ensemble;
    if (e == null) return '—';
    return '${(e.ensembleScore * 100).clamp(0, 100).round()}';
  }

  bool get authenticityHasUnit => ensemble != null;

  String get scamRiskLabel {
    switch (factcheck?.status) {
      case 'SAFE':
        return 'Low';
      case 'CRITICAL':
        return 'Critical';
      case 'UNCERTAIN':
      case 'WARNING':
        return 'Medium';
      case 'VERIFYING':
        return 'Checking';
      default:
        return '—';
    }
  }

  String get callTag {
    switch (factcheck?.status) {
      case 'VERIFYING':
        return 'Analyzing';
      case 'CRITICAL':
        return 'Critical';
      case 'SAFE':
        return 'Safe';
      case 'UNCERTAIN':
      case 'WARNING':
        return 'Uncertain';
      default:
        return wsConnected ? 'Listening' : 'Idle';
    }
  }

  String get riskState {
    switch (factcheck?.status) {
      case 'SAFE':
        return 'Safe';
      case 'CRITICAL':
        return 'Critical';
      case 'VERIFYING':
        return 'Analyzing';
      case 'UNCERTAIN':
      case 'WARNING':
        return 'Suspicious';
      default:
        return 'Awaiting analysis';
    }
  }

  String get riskNote {
    final msg = factcheck?.message;
    if (msg == null || msg.isEmpty) {
      return wsConnected
          ? 'Waiting for factcheck_update from the live call session.'
          : 'Session not connected.';
    }
    return msg;
  }

  /// Needle degrees: -90 safe (left), 0 mid, +90 critical (right).
  double get gaugeDegrees {
    switch (factcheck?.status) {
      case 'SAFE':
        return -90;
      case 'CRITICAL':
        return 82;
      case 'VERIFYING':
      case 'UNCERTAIN':
      case 'WARNING':
        return -4;
      default:
        return -90;
    }
  }

  void _startHealthCheck() {
    _stopHealthCheck();
    _healthCheckTimer = Timer.periodic(_healthCheckInterval, (timer) async {
      final isHealthy = await _api.healthCheck();
      if (!isHealthy && wsConnected) {
        // Backend is down but we think we're connected
        error = 'Backend health check failed';
        wsConnected = false;
        notifyListeners();
      }
    });
  }

  void _stopHealthCheck() {
    _healthCheckTimer?.cancel();
    _healthCheckTimer = null;
  }

  Future<void> startSession() async {
    if (connecting || callId != null) return;
    connecting = true;
    error = null;
    notifyListeners();
    try {
      final init = await _api.initCall();
      callId = init.callId;
      token = init.token;
      notifyListeners();
      await _socket.connect(
        url: _api.websocketUrl(init),
        onJson: _onJson,
        onError: (msg) {
          error = msg;
          wsConnected = false;
          notifyListeners();
        },
        onClose: () {
          wsConnected = false;
          _stopHealthCheck();
          notifyListeners();
        },
      );
      // Start health checks when connected
      _startHealthCheck();
    } catch (e) {
      error = e.toString();
    } finally {
      connecting = false;
      notifyListeners();
    }
  }

  void _onJson(Map<String, dynamic> json) {
    final type = json['type'] as String?;
    switch (type) {
      case 'connected':
        wsConnected = true;
        error = null;
        break;
      case 'config_info':
        dspEnabled = json['dsp_enabled'] == true;
        break;
      case 'factcheck_update':
        factcheck = FactCheckUpdate.fromJson(json);
        break;
      case 'ensemble_update':
        ensemble = EnsembleUpdate.fromJson(json);
        break;
      case 'error':
        error = json['message'] as String? ?? 'WebSocket error';
        break;
      default:
        return;
    }
    notifyListeners();
  }

  Future<EscalationDraft> draftBlockAndReport() async {
    final id = callId;
    final t = token;
    if (id == null || t == null) {
      throw ApiException('No live call session. Wait for /call/init.');
    }
    return _api.draftEscalation(callId: id, token: t);
  }

  Future<void> confirmBlockAndReport(String draftId) async {
    final id = callId;
    final t = token;
    if (id == null || t == null) {
      throw ApiException('No live call session.');
    }
    final result = await _api.confirmEscalation(
      callId: id,
      token: t,
      draftId: draftId,
    );
    lastActionMessage =
        result['delivery_status']?.toString() ?? 'Escalation dispatched';
    notifyListeners();
  }

  Future<void> continueMonitoring() async {
    final id = callId;
    final t = token;
    if (id == null || t == null) {
      throw ApiException('No live call session.');
    }
    final status = await _api.getCallStatus(callId: id, token: t);
    if (status.latestVerdict != null) {
      factcheck = status.latestVerdict;
    }
    lastActionMessage =
        'Monitoring ${status.state} · factchecks: ${status.factcheckCount}';
    notifyListeners();
  }

  /// Upload a video frame for analysis
  Future<Map<String, dynamic>> uploadFrame(List<int> frameBytes) async {
    final id = callId;
    final t = token;
    if (id == null || t == null) {
      throw ApiException('No live call session.');
    }
    return _api.uploadFrame(callId: id, token: t, frameBytes: frameBytes);
  }

  /// Activate AI scambaiter
  Future<Map<String, dynamic>> activateScambaiter() async {
    final id = callId;
    final t = token;
    if (id == null || t == null) {
      throw ApiException('No live call session.');
    }
    return _api.activateScambaiter(callId: id, token: t);
  }

  /// Download forensic dossier PDF
  Future<List<int>> getDossier() async {
    final id = callId;
    final t = token;
    if (id == null || t == null) {
      throw ApiException('No live call session.');
    }
    return _api.getDossier(callId: id, token: t);
  }

  /// Fetch call history
  Future<List<Map<String, dynamic>>> getCallHistory({int limit = 50}) async {
    final t = token;
    if (t == null) {
      throw ApiException('No authentication token.');
    }
    return _api.getCallHistory(token: t, limit: limit);
  }

  /// Continue monitoring current call
  Future<Map<String, dynamic>> resumeMonitoring() async {
    final id = callId;
    final t = token;
    if (id == null || t == null) {
      throw ApiException('No live call session.');
    }
    final result = await _api.continueMonitoring(callId: id, token: t);
    lastActionMessage =
        result['delivery_status']?.toString() ?? 'Monitoring continued';
    notifyListeners();
    return result;
  }

  /// Block and report (future use when endpoint available)
  Future<Map<String, dynamic>> blockAndReport(String reason) async {
    final id = callId;
    final t = token;
    if (id == null || t == null) {
      throw ApiException('No live call session.');
    }
    return _api.blockAndReport(callId: id, token: t, reason: reason);
  }

  @override
  void dispose() {
    _stopHealthCheck();
    _socket.disconnect();
    super.dispose();
  }
}
