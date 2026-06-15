/// App-wide configuration.
class Config {
  /// Base URL of the FastAPI backend.
  ///
  /// - Android emulator reaches the host PC at 10.0.2.2 (NOT 127.0.0.1).
  /// - Real phone on the same Wi-Fi: use your PC's LAN IP, e.g.
  ///     static const String baseUrl = "http://192.168.1.50:8000";
  ///   (run `ipconfig` on the PC to find it, and make sure the firewall allows it).
  static const String baseUrl = "http://10.0.2.2:8000";
}
