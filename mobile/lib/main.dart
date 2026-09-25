import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';

import 'theme.dart';

const genesisPrev = '0000000000000000000000000000000000000000000000000000000000000000';

void main() {
  runApp(const AzielTetherApp());
}

class AzielTetherApp extends StatelessWidget {
  const AzielTetherApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AzielTether',
      debugShowCheckedModeBanner: false,
      theme: buildLightTheme(),
      darkTheme: buildDarkTheme(),
      themeMode: ThemeMode.system,
      home: const TetherPage(),
    );
  }
}

class TetherItem {
  TetherItem({
    required this.createdAt,
    required this.payload,
    required this.prevHash,
    required this.hash,
  });
  final String createdAt;
  final String payload;
  final String prevHash;
  final String hash;
}

String digest(Map<String, Object> body) {
  final keys = body.keys.toList()..sort();
  final raw = '{${keys.map((k) => '${jsonEncode(k)}:${jsonEncode(body[k])}').join(',')}}';
  return sha256.convert(utf8.encode(raw)).toString();
}

class TetherPage extends StatefulWidget {
  const TetherPage({super.key});

  @override
  State<TetherPage> createState() => _TetherPageState();
}

class _TetherPageState extends State<TetherPage> {
  final _payload = TextEditingController();
  final _chain = <TetherItem>[];
  String _status = 'No items yet. Write a note, then start the chain.';

  @override
  void dispose() {
    _payload.dispose();
    super.dispose();
  }

  String _now() => DateTime.now().toUtc().toIso8601String().split('.').first + 'Z';

  void _mint({required bool genesis}) {
    final payload = _payload.text;
    if (payload.trim().isEmpty) {
      setState(() => _status = 'Write a note first.');
      return;
    }
    if (genesis && _chain.isNotEmpty) {
      setState(() => _status = 'This chain already started. Add a note instead.');
      return;
    }
    if (!genesis && _chain.isEmpty) {
      setState(() => _status = 'Start the chain before adding another note.');
      return;
    }
    final ts = _now();
    final prev = genesis ? genesisPrev : _chain.last.hash;
    final body = {
      'created_at': ts,
      'engine_version': '0.1.0',
      'kind': 'work',
      'node_id': 'mobile',
      'payload': payload,
      'prev_hash': prev,
      'report_hash': sha256.convert(utf8.encode(payload)).toString(),
      'scope': 'azieltether',
    };
    final h = digest(body);
    setState(() {
      _chain.add(TetherItem(createdAt: ts, payload: payload, prevHash: prev, hash: h));
      _payload.clear();
      _status = _runVerify();
    });
  }

  String _runVerify() {
    if (_chain.isEmpty) return 'no chain yet';
    final byPrev = <String, List<String>>{};
    for (final item in _chain) {
      byPrev.putIfAbsent(item.prevHash, () => []).add(item.hash);
    }
    final forks = byPrev.values.where((c) => c.toSet().length > 1).length;
    if (forks == 0) return 'Chain checks out. ${_chain.length} item(s).';
    return 'Chain checks out. ${_chain.length} item(s). Forks: $forks. Both children are kept.';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AzielTether')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Keeps a hash-chained copy of your work on this phone.',
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: 8),
          const Text(
            'Prefer central. Peer when down. Reconcile on restore.',
            style: TextStyle(fontStyle: FontStyle.italic),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _payload,
            maxLines: 3,
            decoration: const InputDecoration(labelText: 'Note', alignLabelWithHint: true),
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: () => _mint(genesis: _chain.isEmpty),
            child: Text(_chain.isEmpty ? 'Start chain' : 'Add note'),
          ),
          const SizedBox(height: 8),
          ExpansionTile(
            title: const Text('Advanced'),
            children: [
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton(
                  onPressed: () => setState(() => _status = _runVerify()),
                  child: const Text('Check chain'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(_status),
          const SizedBox(height: 16),
          for (var i = 0; i < _chain.length; i++)
            Card(
              margin: const EdgeInsets.only(bottom: 10),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: SelectableText(
                  [
                    '#$i  ${_chain[i].createdAt}',
                    _chain[i].payload,
                    'prev: ${_chain[i].prevHash.substring(0, 16)}…',
                    'hash: ${_chain[i].hash}',
                  ].join('\n'),
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 12, height: 1.4),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
