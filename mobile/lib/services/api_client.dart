import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../config.dart';

class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => message;
}

/// Minimal HTTP client that attaches the bearer token and unwraps errors.
class ApiClient {
  static String? _token;
  static void setToken(String? t) => _token = t;

  static Map<String, String> _headers([bool json = false]) {
    final h = <String, String>{};
    if (_token != null) h['Authorization'] = 'Bearer $_token';
    if (json) h['Content-Type'] = 'application/json';
    return h;
  }

  static dynamic _handle(http.Response r) {
    dynamic data;
    try {
      data = jsonDecode(r.body);
    } catch (_) {
      data = r.body;
    }
    if (r.statusCode >= 200 && r.statusCode < 300) return data;
    final detail = (data is Map && data['detail'] != null) ? data['detail'] : data;
    throw ApiException(detail is String ? detail : detail.toString());
  }

  static Uri _uri(String path) => Uri.parse('${Config.baseUrl}$path');

  static Future<dynamic> get(String path) async {
    return _handle(await http.get(_uri(path), headers: _headers()));
  }

  static Future<dynamic> post(String path, Map<String, dynamic> body) async {
    return _handle(await http.post(_uri(path), headers: _headers(true), body: jsonEncode(body)));
  }

  static Future<dynamic> uploadImage(
      String path, File image, Map<String, String> fields) async {
    final req = http.MultipartRequest('POST', _uri(path));
    req.headers.addAll(_headers());
    req.files.add(await http.MultipartFile.fromPath('image', image.path));
    fields.forEach((k, v) => req.fields[k] = v);
    final streamed = await req.send();
    return _handle(await http.Response.fromStream(streamed));
  }
}
