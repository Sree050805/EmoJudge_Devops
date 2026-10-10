import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'screens/login_screen.dart';
import 'screens/videos_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final hasToken = prefs.getString('jwt') != null;
  runApp(EmoJudgeApp(startLoggedIn: hasToken));
}

class EmoJudgeApp extends StatelessWidget {
  final bool startLoggedIn;
  const EmoJudgeApp({super.key, required this.startLoggedIn});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EmoJudge',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        colorScheme: const ColorScheme.dark(primary: Colors.amber),
        scaffoldBackgroundColor: const Color(0xFF0D0D0D),
      ),
      home: startLoggedIn ? const VideosScreen() : const LoginScreen(),
    );
  }
}
