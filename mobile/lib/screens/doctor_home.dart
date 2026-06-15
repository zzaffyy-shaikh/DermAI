import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../services/session.dart';
import '../theme.dart';

class DoctorHome extends StatefulWidget {
  final Session session;
  final Future<void> Function() onLogout;
  const DoctorHome({super.key, required this.session, required this.onLogout});

  @override
  State<DoctorHome> createState() => _DoctorHomeState();
}

class _DoctorHomeState extends State<DoctorHome> {
  late Future<dynamic> _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() => _future = ApiClient.get('/consult/queue'));

  Future<void> _act(String id, String action) async {
    try {
      await ApiClient.post('/consult/$id/$action', {});
      _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Consultation Queue'),
        backgroundColor: kDoctor,
        foregroundColor: Colors.white,
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          IconButton(onPressed: widget.onLogout, icon: const Icon(Icons.logout)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => _load(),
        child: FutureBuilder<dynamic>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: [Padding(padding: const EdgeInsets.all(20), child: Text('Error: ${snap.error}'))]);
            }
            final cases = (snap.data as List).cast<Map<String, dynamic>>();
            if (cases.isEmpty) {
              return ListView(children: const [
                Padding(padding: EdgeInsets.all(20), child: Text('Queue is empty. Pull down to refresh.'))
              ]);
            }
            return ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: cases.length,
              itemBuilder: (_, i) {
                final c = cases[i];
                final b = (c['brief'] as Map<String, dynamic>?) ?? {};
                final conf = b['confidence'] != null
                    ? ' · ${((b['confidence'] as num) * 100).toStringAsFixed(0)}%'
                    : '';
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Text('${b['disease'] ?? 'Unknown'}',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                        const SizedBox(width: 8),
                        if (b['urgent'] == true)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(color: kErr, borderRadius: BorderRadius.circular(999)),
                            child: const Text('URGENT', style: TextStyle(color: Colors.white, fontSize: 11)),
                          ),
                      ]),
                      const SizedBox(height: 4),
                      Text('patient ${c['patient_id']} · ${c['mode']} consult$conf',
                          style: const TextStyle(color: Colors.black54, fontSize: 12.5)),
                      if (c['note'] != null)
                        Padding(padding: const EdgeInsets.only(top: 4), child: Text('note: ${c['note']}')),
                      const SizedBox(height: 10),
                      Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                        FilledButton(
                          style: FilledButton.styleFrom(backgroundColor: kDoctor),
                          onPressed: () => _act(c['id'], 'accept'),
                          child: const Text('Accept'),
                        ),
                        const SizedBox(width: 8),
                        OutlinedButton(onPressed: () => _act(c['id'], 'close'), child: const Text('Close')),
                      ]),
                    ]),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
