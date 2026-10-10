import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'videos_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _idCtrl = TextEditingController();
  final _pwCtrl = TextEditingController();
  bool _loading = false;
  String? _error;
  bool _obscure = true;

  Future<void> _login() async {
    setState(() { _loading = true; _error = null; });
    final token = await ApiService.login(_idCtrl.text.trim(), _pwCtrl.text);
    setState(() => _loading = false);
    if (token != null && mounted) {
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const VideosScreen()));
    } else {
      setState(() => _error = 'Invalid Attorney ID or Password.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0D0D),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(32),
          child: Column(
            children: [
              const Text('⚖ EMOJUDGE',
                  style: TextStyle(color: Colors.amber, fontSize: 28, fontWeight: FontWeight.bold, letterSpacing: 3)),
              const SizedBox(height: 8),
              const Text('AI-powered emotion analysis for legal professionals.',
                  style: TextStyle(color: Colors.amber, fontSize: 13), textAlign: TextAlign.center),
              const SizedBox(height: 32),
              _field(_idCtrl, 'Attorney ID', false),
              const SizedBox(height: 12),
              _field(_pwCtrl, 'Password', _obscure, suffix: IconButton(
                icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility, color: Colors.white54),
                onPressed: () => setState(() => _obscure = !_obscure),
              )),
              if (_error != null) ...[
                const SizedBox(height: 10),
                Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 13)),
              ],
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _loading ? null : _login,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.amber, foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  child: _loading
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                      : const Text('Login', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _field(TextEditingController ctrl, String hint, bool obscure, {Widget? suffix}) {
    return TextField(
      controller: ctrl,
      obscureText: obscure,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: Colors.white38),
        filled: true,
        fillColor: const Color(0xFF1A1A1A),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Colors.amber)),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Colors.amber38)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Colors.amber)),
        suffixIcon: suffix,
      ),
    );
  }
}
