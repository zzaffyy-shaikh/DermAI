import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../services/api_client.dart';
import '../services/session.dart';
import '../theme.dart';

class PatientHome extends StatefulWidget {
  final Session session;
  final Future<void> Function() onLogout;
  const PatientHome({super.key, required this.session, required this.onLogout});

  @override
  State<PatientHome> createState() => _PatientHomeState();
}

class _PatientHomeState extends State<PatientHome> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('DermAI'),
        backgroundColor: kPatient,
        foregroundColor: Colors.white,
        actions: [
          IconButton(onPressed: widget.onLogout, icon: const Icon(Icons.logout)),
        ],
      ),
      body: IndexedStack(
        index: _tab,
        children: const [DiagnoseTab(), HistoryTab()],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.camera_alt_outlined), label: 'Diagnose'),
          NavigationDestination(icon: Icon(Icons.history), label: 'History'),
        ],
      ),
    );
  }
}

/* ----------------------------- Diagnose ----------------------------- */
class DiagnoseTab extends StatefulWidget {
  const DiagnoseTab({super.key});
  @override
  State<DiagnoseTab> createState() => _DiagnoseTabState();
}

class _DiagnoseTabState extends State<DiagnoseTab> {
  static const regions = [
    'face', 'scalp', 'neck', 'chest', 'back', 'arm', 'forearm', 'hand', 'abdomen', 'leg', 'foot'
  ];

  final _picker = ImagePicker();
  File? _image;
  String? _region;
  bool _busy = false;
  String? _error;

  Map<String, dynamic>? _brief;
  String? _sessionId;
  final List<Map<String, String>> _messages = [];
  bool _awaiting = false;
  bool _done = false;
  final _answer = TextEditingController();
  final _note = TextEditingController();
  String? _consultMsg;

  Future<void> _pick(ImageSource src) async {
    final x = await _picker.pickImage(source: src, maxWidth: 1280);
    if (x != null) setState(() => _image = File(x.path));
  }

  Future<void> _diagnose() async {
    if (_image == null) {
      setState(() => _error = 'Please choose an image first.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _brief = null;
      _messages.clear();
      _done = false;
      _consultMsg = null;
    });
    try {
      final fields = <String, String>{};
      if (_region != null) fields['body_region'] = _region!;
      final data = await ApiClient.uploadImage('/diagnose', _image!, fields) as Map<String, dynamic>;
      setState(() {
        _sessionId = data['session_id'];
        _brief = data['brief'] as Map<String, dynamic>;
        _messages.add({'role': 'assistant', 'text': data['message']});
        _awaiting = data['awaiting_answer'] == true;
        _done = !_awaiting;
      });
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _send() async {
    final text = _answer.text.trim();
    if (text.isEmpty || _sessionId == null) return;
    setState(() {
      _messages.add({'role': 'user', 'text': text});
      _answer.clear();
      _awaiting = false;
    });
    try {
      final turn = await ApiClient.post('/chat/answer', {
        'session_id': _sessionId,
        'answer': text,
      }) as Map<String, dynamic>;
      setState(() {
        _messages.add({'role': 'assistant', 'text': turn['message']});
        _done = turn['done'] == true;
        _awaiting = !_done;
      });
    } catch (e) {
      setState(() {
        _messages.add({'role': 'assistant', 'text': '⚠️ $e'});
        _awaiting = true;
      });
    }
  }

  Future<void> _requestConsult() async {
    try {
      final c = await ApiClient.post('/consult/request', {
        'session_id': _sessionId,
        'mode': 'video',
        'note': _note.text.trim().isEmpty ? null : _note.text.trim(),
      }) as Map<String, dynamic>;
      setState(() => _consultMsg = '✅ Video consultation requested (case ${c['id']}).');
    } catch (e) {
      setState(() => _consultMsg = 'Error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              const Text('Skin screening', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
              const SizedBox(height: 12),
              if (_image != null)
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.file(_image!, height: 180, fit: BoxFit.cover),
                ),
              const SizedBox(height: 10),
              Row(children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _pick(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt), label: const Text('Camera'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _pick(ImageSource.gallery),
                    icon: const Icon(Icons.photo_library), label: const Text('Gallery'),
                  ),
                ),
              ]),
              const SizedBox(height: 10),
              DropdownButtonFormField<String>(
                value: _region,
                decoration: const InputDecoration(labelText: 'Affected body region (optional)'),
                items: regions.map((r) => DropdownMenuItem(value: r, child: Text(r))).toList(),
                onChanged: (v) => setState(() => _region = v),
              ),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: _busy ? null : _diagnose,
                child: _busy
                    ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('Diagnose'),
              ),
              if (_error != null) Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Text(_error!, style: const TextStyle(color: kErr)),
              ),
            ]),
          ),
        ),

        if (_brief != null) _briefCard(_brief!),
        if (_messages.isNotEmpty) _chatCard(),
        if (_done) _consultCard(),
      ],
    );
  }

  Widget _briefCard(Map<String, dynamic> b) {
    final conf = ((b['confidence'] as num) * 100).toStringAsFixed(1);
    final mode = b['mode'] as String;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Text('Result', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            const SizedBox(width: 8),
            _chip(mode, colorForMode(mode)),
            if (b['urgent'] == true) ...[const SizedBox(width: 6), _chip('URGENT', kErr)],
          ]),
          const SizedBox(height: 12),
          _kv('Disease', '${b['disease']}'),
          _kv('Confidence', '$conf%'),
          _kv('Region', '${b['body_region'] ?? '—'}'),
          _kv('Severity', '${b['severity'] ?? '—'}'),
          _kv('Image quality', '${b['image_quality']}'),
        ]),
      ),
    );
  }

  Widget _chatCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Follow-up questions', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          ..._messages.map((m) => Align(
                alignment: m['role'] == 'user' ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  margin: const EdgeInsets.symmetric(vertical: 4),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                  constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.7),
                  decoration: BoxDecoration(
                    color: m['role'] == 'user' ? kPatient : const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Text(m['text'] ?? '',
                      style: TextStyle(color: m['role'] == 'user' ? Colors.white : Colors.black87)),
                ),
              )),
          if (_done)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text('✓ Screening complete', style: TextStyle(color: kOk, fontWeight: FontWeight.w700)),
            )
          else
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Row(children: [
                Expanded(
                  child: TextField(
                    controller: _answer,
                    enabled: _awaiting,
                    decoration: const InputDecoration(hintText: 'Type your answer...'),
                    onSubmitted: (_) => _send(),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(onPressed: _awaiting ? _send : null, child: const Text('Send')),
              ]),
            ),
        ]),
      ),
    );
  }

  Widget _consultCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Consult a doctor 🎥', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          const Text('Consultations are conducted over video.', style: TextStyle(color: Colors.black54)),
          const SizedBox(height: 10),
          TextField(controller: _note, decoration: const InputDecoration(labelText: 'Note (optional)')),
          const SizedBox(height: 10),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: kDoctor),
            onPressed: _requestConsult,
            child: const Text('Request video consultation'),
          ),
          if (_consultMsg != null)
            Padding(padding: const EdgeInsets.only(top: 10), child: Text(_consultMsg!)),
        ]),
      ),
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [
          SizedBox(width: 120, child: Text(k, style: const TextStyle(color: Colors.black54))),
          Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w600))),
        ]),
      );

  Widget _chip(String text, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
        decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(999)),
        child: Text(text, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)),
      );
}

/* ----------------------------- History ----------------------------- */
class HistoryTab extends StatefulWidget {
  const HistoryTab({super.key});
  @override
  State<HistoryTab> createState() => _HistoryTabState();
}

class _HistoryTabState extends State<HistoryTab> {
  late Future<dynamic> _future;

  @override
  void initState() {
    super.initState();
    _future = ApiClient.get('/history');
  }

  void _refresh() => setState(() => _future = ApiClient.get('/history'));

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async => _refresh(),
      child: FutureBuilder<dynamic>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return ListView(children: [Padding(padding: const EdgeInsets.all(20), child: Text('Error: ${snap.error}'))]);
          }
          final items = (snap.data as List).cast<Map<String, dynamic>>();
          if (items.isEmpty) {
            return ListView(children: const [Padding(padding: EdgeInsets.all(20), child: Text('No screenings yet.'))]);
          }
          return ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: items.length,
            itemBuilder: (_, i) {
              final s = items[i];
              final conf = ((s['confidence'] as num) * 100).toStringAsFixed(1);
              return Card(
                child: ListTile(
                  title: Text('${s['disease']}'),
                  subtitle: Text('confidence $conf% · ${s['done'] == true ? 'completed' : 'in progress'}'),
                  trailing: s['urgent'] == true
                      ? const Icon(Icons.warning, color: kErr)
                      : Icon(Icons.circle, size: 12, color: colorForMode(s['mode'])),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
