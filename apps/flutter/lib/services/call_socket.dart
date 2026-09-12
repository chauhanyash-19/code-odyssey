import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

typedef JsonHandler = void Function(Map<String, dynamic> json);
typedef BytesHandler = void Function(List<int> bytes);

class CallSocket {
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _sub;
  Timer? _keepaliveTimer;
  int _reconnectAttempts = 0;
  static const _maxReconnect = 5;
  static const _reconnectDelay = Duration(seconds: 2);
  static const _keepaliveInterval = Duration(minutes: 5); // Send ping every 5 minutes to prevent Render spindown

  bool get isConnected => _channel != null;

  Future<void> connect({
    required String url,
    required JsonHandler onJson,
    BytesHandler? onBytes,
    void Function(String message)? onError,
    void Function()? onClose,
  }) async {
    await disconnect();
    final uri = Uri.parse(url);
    _channel = WebSocketChannel.connect(uri);
    await _channel!.ready;
    _reconnectAttempts = 0;

    // Start keepalive timer to prevent Render spindown
    _startKeepalive();

    _sub = _channel!.stream.listen(
      (event) {
        if (event is String) {
          try {
            final decoded = jsonDecode(event);
            if (decoded is Map<String, dynamic>) {
              onJson(decoded);
            }
          } catch (_) {}
        } else if (event is List<int>) {
          onBytes?.call(event);
        }
      },
      onError: (Object err) {
        onError?.call(err.toString());
      },
      onDone: () {
        _stopKeepalive();
        onClose?.call();
        _attemptReconnect(
          url: url,
          onJson: onJson,
          onBytes: onBytes,
          onError: onError,
          onClose: onClose,
        );
      },
    );
  }

  void _startKeepalive() {
    _stopKeepalive(); // Clear any existing timer
    _keepaliveTimer = Timer.periodic(_keepaliveInterval, (timer) {
      if (_channel != null) {
        try {
          // Send a ping message to keep the connection alive
          _channel!.sink.add(jsonEncode({'type': 'ping', 'timestamp': DateTime.now().toIso8601String()}));
        } catch (e) {
          // If sending fails, the connection might be dead
          timer.cancel();
        }
      }
    });
  }

  void _stopKeepalive() {
    _keepaliveTimer?.cancel();
    _keepaliveTimer = null;
  }

  void _attemptReconnect({
    required String url,
    required JsonHandler onJson,
    BytesHandler? onBytes,
    void Function(String message)? onError,
    void Function()? onClose,
  }) {
    if (_reconnectAttempts >= _maxReconnect) return;
    _reconnectAttempts++;
    Future<void>.delayed(_reconnectDelay, () {
      connect(
        url: url,
        onJson: onJson,
        onBytes: onBytes,
        onError: onError,
        onClose: onClose,
      ).catchError((Object err) {
        onError?.call(err.toString());
      });
    });
  }

  Future<void> disconnect() async {
    _stopKeepalive();
    await _sub?.cancel();
    _sub = null;
    await _channel?.sink.close();
    _channel = null;
  }
}
