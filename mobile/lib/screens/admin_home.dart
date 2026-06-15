import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../services/session.dart';
import '../theme.dart';

class AdminHome extends StatefulWidget {
  final Session session;
  final Future<void> Function() onLogout;
  const AdminHome({super.key, required this.session, required this.onLogout});

  @override
  State<AdminHome> createState() => _AdminHomeState();
}

class _AdminHomeState extends State<AdminHome> {
  Map<String, dynamic>? _stats;
  List<Map<String, dynamic>> _doctors = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final stats = await ApiClient.get('/admin/stats') as Map<String, dynamic>;
      final docs = (await ApiClient.get('/admin/doctors') as List).cast<Map<String, dynamic>>();
      setState(() {
        _stats = stats;
        _doctors = docs;
      });
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _verify(String uid, bool approved) async {
    try {
      await ApiClient.post('/admin/doctors/verify', {'uid': uid, 'approved': approved});
      _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Administration'),
        backgroundColor: kAdmin,
        foregroundColor: Colors.white,
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          IconButton(onPressed: widget.onLogout, icon: const Icon(Icons.logout)),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (_error != null) Text('Error: $_error', style: const TextStyle(color: kErr)),
                  if (_stats != null) _statsCard(_stats!),
                  const SizedBox(height: 8),
                  const Text('Doctors', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  if (_doctors.isEmpty)
                    const Padding(padding: EdgeInsets.all(8), child: Text('No doctor accounts yet.')),
                  ..._doctors.map(_doctorTile),
                ],
              ),
            ),
    );
  }

  Widget _statsCard(Map<String, dynamic> s) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Wrap(
          spacing: 12,
          runSpacing: 12,
          children: s.entries.map((e) {
            return Container(
              width: 140,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(e.key.replaceAll('_', ' '),
                    style: const TextStyle(fontSize: 11, color: Colors.black54)),
                const SizedBox(height: 2),
                Text('${e.value}', style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w700)),
              ]),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _doctorTile(Map<String, dynamic> d) {
    final verified = d['verified'] == true;
    return Card(
      child: ListTile(
        title: Text(d['name'] ?? d['username']),
        subtitle: Text('@${d['username']} · ${d['specialization'] ?? '—'}'),
        trailing: Row(mainAxisSize: MainAxisSize.min, children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
            decoration: BoxDecoration(
              color: verified ? kOk : kWarn,
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(verified ? 'verified' : 'pending',
                style: const TextStyle(color: Colors.white, fontSize: 11)),
          ),
          const SizedBox(width: 8),
          verified
              ? OutlinedButton(onPressed: () => _verify(d['uid'], false), child: const Text('Revoke'))
              : FilledButton(
                  style: FilledButton.styleFrom(backgroundColor: kOk),
                  onPressed: () => _verify(d['uid'], true),
                  child: const Text('Approve'),
                ),
        ]),
      ),
    );
  }
}
