import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const String _base = 'http://127.0.0.1:5000';
  static const String _fastapi = 'http://127.0.0.1:8000';

  // ── Auth ──────────────────────────────────────────────────────────────────

  static Future<String?> login(String attorneyId, String password) async {
    final res = await http.post(
      Uri.parse('$_base/api/token'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'attorney_id': attorneyId, 'password': password}),
    );
    if (res.statusCode == 200) {
      final token = jsonDecode(res.body)['token'] as String;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('jwt', token);
      await prefs.setString('attorney_id', attorneyId);
      return token;
    }
    return null;
  }

  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('jwt');
    await prefs.remove('attorney_id');
  }

  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('jwt');
  }

  // ── Emotion analysis ──────────────────────────────────────────────────────

  static Future<Map<String, dynamic>?> analyzeEmotion(
      String videoPath, double time) async {
    final res = await http.post(
      Uri.parse('$_fastapi/analyze_emotion/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'video_path': videoPath, 'time': time}),
    );
    if (res.statusCode == 200) return jsonDecode(res.body);
    return null;
  }

  static Future<List<dynamic>> getEmotionHistory(String videoName) async {
    final res = await http.get(Uri.parse('$_fastapi/emotion_history/$videoName'));
    if (res.statusCode == 200) {
      return jsonDecode(res.body)['history'] ?? [];
    }
    return [];
  }

  // ── Case notes ────────────────────────────────────────────────────────────

  static Future<List<dynamic>> getNotes() async {
    final token = await getToken();
    final res = await http.get(
      Uri.parse('$_base/api/notes'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (res.statusCode == 200) return jsonDecode(res.body);
    return [];
  }

  static Future<bool> saveNote(String video, String note) async {
    final token = await getToken();
    final res = await http.post(
      Uri.parse('$_base/api/notes'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({'video': video, 'note': note}),
    );
    return res.statusCode == 200;
  }

  static Future<void> deleteNote(int id) async {
    final token = await getToken();
    await http.delete(
      Uri.parse('$_base/api/notes/$id'),
      headers: {'Authorization': 'Bearer $token'},
    );
  }
}
