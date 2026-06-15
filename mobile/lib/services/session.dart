import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

/// Authenticated session: token + public user fields.
class Session {
  final String token;
  final String uid;
  final String role;
  final String username;
  final String? name;

  Session({
    required this.token,
    required this.uid,
    required this.role,
    required this.username,
    this.name,
  });

  /// Build from the /auth/login or /auth/register response.
  factory Session.fromAuth(Map<String, dynamic> data) {
    final user = data['user'] as Map<String, dynamic>;
    return Session(
      token: data['token'] as String,
      uid: user['uid'] as String,
      role: user['role'] as String,
      username: user['username'] as String,
      name: user['name'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'token': token,
        'uid': uid,
        'role': role,
        'username': username,
        'name': name,
      };

  factory Session.fromJson(Map<String, dynamic> j) => Session(
        token: j['token'],
        uid: j['uid'],
        role: j['role'],
        username: j['username'],
        name: j['name'],
      );
}

class SessionStore {
  static const _key = 'dermai.session';

  static Future<void> save(Session s) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_key, jsonEncode(s.toJson()));
  }

  static Future<Session?> load() async {
    final p = await SharedPreferences.getInstance();
    final raw = p.getString(_key);
    if (raw == null) return null;
    try {
      return Session.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  static Future<void> clear() async {
    final p = await SharedPreferences.getInstance();
    await p.remove(_key);
  }
}
