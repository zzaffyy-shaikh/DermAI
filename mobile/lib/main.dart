import 'package:flutter/material.dart';

import 'services/api_client.dart';
import 'services/session.dart';
import 'theme.dart';
import 'screens/login_screen.dart';
import 'screens/patient_home.dart';
import 'screens/doctor_home.dart';
import 'screens/admin_home.dart';

void main() => runApp(const DermAIApp());

class DermAIApp extends StatelessWidget {
  const DermAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'DermAI',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      home: const RootGate(),
    );
  }
}

/// Decides which screen to show based on the stored session + role.
class RootGate extends StatefulWidget {
  const RootGate({super.key});
  @override
  State<RootGate> createState() => _RootGateState();
}

class _RootGateState extends State<RootGate> {
  Session? _session;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    final s = await SessionStore.load();
    if (s != null) ApiClient.setToken(s.token);
    setState(() {
      _session = s;
      _loading = false;
    });
  }

  Future<void> _onLogin(Session s) async {
    ApiClient.setToken(s.token);
    await SessionStore.save(s);
    setState(() => _session = s);
  }

  Future<void> _onLogout() async {
    try {
      await ApiClient.post('/auth/logout', {});
    } catch (_) {}
    await SessionStore.clear();
    ApiClient.setToken(null);
    setState(() => _session = null);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final s = _session;
    if (s == null) return LoginScreen(onLogin: _onLogin);
    switch (s.role) {
      case 'doctor':
        return DoctorHome(session: s, onLogout: _onLogout);
      case 'admin':
        return AdminHome(session: s, onLogout: _onLogout);
      default:
        return PatientHome(session: s, onLogout: _onLogout);
    }
  }
}
