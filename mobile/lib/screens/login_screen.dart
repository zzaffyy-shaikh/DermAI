import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../services/session.dart';
import '../theme.dart';

class LoginScreen extends StatefulWidget {
  final Future<void> Function(Session) onLogin;
  const LoginScreen({super.key, required this.onLogin});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _signup = false;
  String _role = 'patient';
  bool _busy = false;
  String? _error;

  final _username = TextEditingController();
  final _password = TextEditingController();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _age = TextEditingController();
  final _specialization = TextEditingController();
  String? _gender;

  @override
  void dispose() {
    for (final c in [_username, _password, _name, _email, _age, _specialization]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final Map<String, dynamic> data;
      if (_signup) {
        final body = <String, dynamic>{
          'username': _username.text.trim(),
          'password': _password.text,
          'role': _role,
          'name': _name.text.trim().isEmpty ? null : _name.text.trim(),
          'email': _email.text.trim().isEmpty ? null : _email.text.trim(),
        };
        if (_role == 'patient') {
          body['age'] = _age.text.trim().isEmpty ? null : int.tryParse(_age.text.trim());
          body['gender'] = _gender;
        } else {
          body['specialization'] =
              _specialization.text.trim().isEmpty ? null : _specialization.text.trim();
        }
        data = await ApiClient.post('/auth/register', body) as Map<String, dynamic>;
      } else {
        data = await ApiClient.post('/auth/login', {
          'username': _username.text.trim(),
          'password': _password.text,
        }) as Map<String, dynamic>;
      }
      await widget.onLogin(Session.fromAuth(data));
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(22),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Center(
                      child: Text('DermAI',
                          style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800, color: kPatient)),
                    ),
                    const SizedBox(height: 4),
                    const Center(
                        child: Text('AI-powered skin disease screening',
                            style: TextStyle(color: Colors.black54))),
                    const SizedBox(height: 18),

                    // Sign in / Create account toggle
                    SegmentedButton<bool>(
                      segments: const [
                        ButtonSegment(value: false, label: Text('Sign in')),
                        ButtonSegment(value: true, label: Text('Create account')),
                      ],
                      selected: {_signup},
                      onSelectionChanged: (s) => setState(() => _signup = s.first),
                    ),
                    const SizedBox(height: 14),

                    if (_signup) ...[
                      SegmentedButton<String>(
                        segments: const [
                          ButtonSegment(value: 'patient', label: Text('🧑 Patient')),
                          ButtonSegment(value: 'doctor', label: Text('👨‍⚕️ Doctor')),
                        ],
                        selected: {_role},
                        onSelectionChanged: (s) => setState(() => _role = s.first),
                      ),
                      const SizedBox(height: 12),
                    ],

                    TextField(
                      controller: _username,
                      decoration: const InputDecoration(labelText: 'Username'),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _password,
                      obscureText: true,
                      decoration: const InputDecoration(labelText: 'Password'),
                    ),

                    if (_signup) ...[
                      const SizedBox(height: 10),
                      TextField(controller: _name, decoration: const InputDecoration(labelText: 'Full name')),
                      const SizedBox(height: 10),
                      TextField(
                          controller: _email,
                          keyboardType: TextInputType.emailAddress,
                          decoration: const InputDecoration(labelText: 'Email')),
                      if (_role == 'patient') ...[
                        const SizedBox(height: 10),
                        Row(children: [
                          Expanded(
                            child: TextField(
                                controller: _age,
                                keyboardType: TextInputType.number,
                                decoration: const InputDecoration(labelText: 'Age')),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: DropdownButtonFormField<String>(
                              value: _gender,
                              decoration: const InputDecoration(labelText: 'Gender'),
                              items: const [
                                DropdownMenuItem(value: 'Male', child: Text('Male')),
                                DropdownMenuItem(value: 'Female', child: Text('Female')),
                                DropdownMenuItem(value: 'Other', child: Text('Other')),
                              ],
                              onChanged: (v) => setState(() => _gender = v),
                            ),
                          ),
                        ]),
                      ] else ...[
                        const SizedBox(height: 10),
                        TextField(
                            controller: _specialization,
                            decoration: const InputDecoration(labelText: 'Specialization')),
                        const Padding(
                          padding: EdgeInsets.only(top: 8),
                          child: Text('Doctor accounts require admin verification.',
                              style: TextStyle(fontSize: 12, color: Colors.black54)),
                        ),
                      ],
                    ],

                    if (_error != null) ...[
                      const SizedBox(height: 12),
                      Text(_error!, style: const TextStyle(color: kErr, fontSize: 13)),
                    ],
                    const SizedBox(height: 18),
                    FilledButton(
                      onPressed: _busy ? null : _submit,
                      child: _busy
                          ? const SizedBox(
                              height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : Text(_signup ? 'Create account' : 'Sign in'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
