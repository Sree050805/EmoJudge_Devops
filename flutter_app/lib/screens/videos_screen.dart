import 'dart:async';
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/api_service.dart';
import 'login_screen.dart';

const _videos = [
  {'file': 'video1.mp4', 'label': 'Witness 1: Late-night burglary at a convenience store.', 'context': 'burglary'},
  {'file': 'video2.mp4', 'label': 'Witness 2: Confrontation during a home invasion.', 'context': 'home'},
  {'file': 'video3.mp4', 'label': 'Witness 3: Stolen documents in a corporate fraud case.', 'context': 'fraud'},
  {'file': 'video4.mp4', 'label': 'Witness 4: Hit-and-run accident downtown.', 'context': 'accident'},
  {'file': 'video5.mp4', 'label': 'Witness 5: Suspicious behavior in bank fraud.', 'context': 'fraud'},
];

const _emotions = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral'];
const _colors = [Colors.red, Colors.purple, Colors.blue, Colors.green, Colors.grey, Colors.orange, Colors.white70];

class VideosScreen extends StatefulWidget {
  const VideosScreen({super.key});
  @override
  State<VideosScreen> createState() => _VideosScreenState();
}

class _VideosScreenState extends State<VideosScreen> {
  String _filter = 'all';
  Map<String, dynamic>? _currentResult;
  String? _selectedVideo;
  bool _analyzing = false;
  final List<Map<String, dynamic>> _timeline = [];
  final List<Map<String, dynamic>> _notes = [];
  final _noteCtrl = TextEditingController();
  Timer? _timer;

  List<Map<String, dynamic>> get _filteredVideos => _videos
      .where((v) => _filter == 'all' || v['context'] == _filter)
      .toList();

  void _selectVideo(String file) {
    setState(() {
      _selectedVideo = file;
      _currentResult = null;
      _timeline.clear();
    });
    _loadNotes();
    _timer?.cancel();
    // Simulate periodic analysis (in real app, hook into video_player position)
    _timer = Timer.periodic(const Duration(seconds: 4), (_) => _analyze(0));
  }

  Future<void> _analyze(double time) async {
    if (_selectedVideo == null) return;
    setState(() => _analyzing = true);
    final result = await ApiService.analyzeEmotion(_selectedVideo!, time);
    if (result != null && mounted) {
      setState(() {
        _currentResult = result;
        _analyzing = false;
        if (_timeline.length >= 30) _timeline.removeAt(0);
        _timeline.add({'time': time, 'scores': result['scores']});
      });
    } else {
      setState(() => _analyzing = false);
    }
  }

  Future<void> _loadNotes() async {
    final all = await ApiService.getNotes();
    setState(() {
      _notes
        ..clear()
        ..addAll(all.where((n) => n['video'] == _selectedVideo).cast<Map<String, dynamic>>());
    });
  }

  Future<void> _saveNote() async {
    final text = _noteCtrl.text.trim();
    if (text.isEmpty || _selectedVideo == null) return;
    await ApiService.saveNote(_selectedVideo!, text);
    _noteCtrl.clear();
    _loadNotes();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _noteCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0D0D),
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: const Text('⚖ EMOJUDGE', style: TextStyle(color: Colors.amber, letterSpacing: 2)),
        actions: [
          TextButton(
            onPressed: () async {
              await ApiService.logout();
              if (mounted) Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const LoginScreen()));
            },
            child: const Text('Logout', style: TextStyle(color: Colors.amber)),
          )
        ],
      ),
      body: _selectedVideo == null ? _videoGrid() : _analysisView(),
    );
  }

  Widget _videoGrid() {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: DropdownButton<String>(
            value: _filter,
            dropdownColor: const Color(0xFF1A1A1A),
            style: const TextStyle(color: Colors.amber),
            items: ['all', 'burglary', 'home', 'fraud', 'accident', 'harassment', 'cyber', 'murder']
                .map((f) => DropdownMenuItem(value: f, child: Text(f.toUpperCase())))
                .toList(),
            onChanged: (v) => setState(() => _filter = v!),
          ),
        ),
        Expanded(
          child: GridView.builder(
            padding: const EdgeInsets.all(12),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2, childAspectRatio: 1.4, crossAxisSpacing: 12, mainAxisSpacing: 12),
            itemCount: _filteredVideos.length,
            itemBuilder: (_, i) {
              final v = _filteredVideos[i];
              return GestureDetector(
                onTap: () => _selectVideo(v['file']!),
                child: Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFF1A1A1A),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.amber.withOpacity(.3)),
                  ),
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.play_circle_fill, color: Colors.amber, size: 40),
                      const SizedBox(height: 8),
                      Text(v['file']!, style: const TextStyle(color: Colors.amber, fontWeight: FontWeight.bold, fontSize: 13)),
                      const SizedBox(height: 4),
                      Text(v['label']!, style: const TextStyle(color: Colors.white54, fontSize: 11), textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _analysisView() {
    final scores = (_currentResult?['scores'] as Map?)?.cast<String, dynamic>();
    return Column(
      children: [
        // Back bar
        Container(
          color: Colors.black,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(
            children: [
              IconButton(icon: const Icon(Icons.arrow_back, color: Colors.amber), onPressed: () { _timer?.cancel(); setState(() => _selectedVideo = null); }),
              Text(_selectedVideo ?? '', style: const TextStyle(color: Colors.amber, fontWeight: FontWeight.bold)),
              const Spacer(),
              if (_analyzing) const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.amber)),
            ],
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Emotion + confidence
                if (_currentResult != null) ...[
                  _card(child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(_currentResult!['detected_emotion']?.toString().toUpperCase() ?? '—',
                          style: const TextStyle(color: Colors.amber, fontSize: 24, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 6),
                      Text('Confidence: ${_currentResult!['confidence']}%', style: const TextStyle(color: Colors.white70, fontSize: 13)),
                      const SizedBox(height: 6),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: ((_currentResult!['confidence'] as num?) ?? 0) / 100,
                          backgroundColor: Colors.white12,
                          color: Colors.amber,
                          minHeight: 8,
                        ),
                      ),
                    ],
                  )),
                  const SizedBox(height: 10),
                  // Advice
                  _card(child: Text(_currentResult!['advice'] ?? '—',
                      style: const TextStyle(color: Colors.white, fontSize: 13, height: 1.5))),
                  const SizedBox(height: 10),
                  // Scores
                  if (scores != null)
                    _card(child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('All Scores', style: TextStyle(color: Colors.amber, fontSize: 13, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 8),
                        ...scores.entries.map((e) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 3),
                          child: Row(children: [
                            SizedBox(width: 70, child: Text(e.key, style: const TextStyle(color: Colors.white70, fontSize: 12))),
                            Expanded(child: ClipRRect(
                              borderRadius: BorderRadius.circular(3),
                              child: LinearProgressIndicator(
                                value: (e.value as num) / 100,
                                backgroundColor: Colors.white12,
                                color: Colors.amber,
                                minHeight: 6,
                              ),
                            )),
                            const SizedBox(width: 6),
                            Text('${e.value}%', style: const TextStyle(color: Colors.amber, fontSize: 11)),
                          ]),
                        )),
                      ],
                    )),
                ],
                const SizedBox(height: 10),
                // Timeline chart
                if (_timeline.isNotEmpty)
                  _card(child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Emotion Timeline', style: TextStyle(color: Colors.amber, fontSize: 13, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      SizedBox(height: 160, child: _buildChart()),
                    ],
                  )),
                const SizedBox(height: 10),
                // Case notes
                _card(child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Case Notes', style: TextStyle(color: Colors.amber, fontSize: 13, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _noteCtrl,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      maxLines: 3,
                      decoration: InputDecoration(
                        hintText: 'Add a note…',
                        hintStyle: const TextStyle(color: Colors.white38),
                        filled: true, fillColor: const Color(0xFF111111),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: Colors.amber38)),
                        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: Colors.amber38)),
                      ),
                    ),
                    const SizedBox(height: 6),
                    ElevatedButton(
                      onPressed: _saveNote,
                      style: ElevatedButton.styleFrom(backgroundColor: Colors.amber, foregroundColor: Colors.black),
                      child: const Text('Save Note', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                    const SizedBox(height: 8),
                    ..._notes.map((n) => Container(
                      margin: const EdgeInsets.only(bottom: 6),
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(color: const Color(0xFF1A1A1A), borderRadius: BorderRadius.circular(6)),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(n['note'] ?? '', style: const TextStyle(color: Colors.white, fontSize: 12)),
                              Text(n['created_at'] ?? '', style: const TextStyle(color: Colors.white38, fontSize: 10)),
                            ],
                          )),
                          IconButton(
                            icon: const Icon(Icons.close, color: Colors.red, size: 16),
                            onPressed: () async { await ApiService.deleteNote(n['id']); _loadNotes(); },
                            padding: EdgeInsets.zero, constraints: const BoxConstraints(),
                          ),
                        ],
                      ),
                    )),
                  ],
                )),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildChart() {
    final spots = <String, List<FlSpot>>{};
    for (var e in _emotions) spots[e] = [];
    for (int i = 0; i < _timeline.length; i++) {
      final s = (_timeline[i]['scores'] as Map?)?.cast<String, dynamic>() ?? {};
      for (var e in _emotions) spots[e]!.add(FlSpot(i.toDouble(), (s[e] as num? ?? 0).toDouble()));
    }
    return LineChart(LineChartData(
      backgroundColor: const Color(0xFF111111),
      gridData: FlGridData(getDrawingHorizontalLine: (_) => FlLine(color: Colors.white12, strokeWidth: 0.5)),
      borderData: FlBorderData(show: false),
      titlesData: FlTitlesData(
        leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 28,
            getTitlesWidget: (v, _) => Text('${v.toInt()}', style: const TextStyle(color: Colors.white38, fontSize: 9)))),
        bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
      ),
      minY: 0, maxY: 100,
      lineBarsData: _emotions.asMap().entries.map((entry) => LineChartBarData(
        spots: spots[entry.value]!,
        color: _colors[entry.key],
        barWidth: 1.5,
        dotData: FlDotData(show: false),
        isCurved: true,
      )).toList(),
    ));
  }

  Widget _card({required Widget child}) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: const Color(0xFF1A1A1A),
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: Colors.amber.withOpacity(.2)),
    ),
    child: child,
  );
}
