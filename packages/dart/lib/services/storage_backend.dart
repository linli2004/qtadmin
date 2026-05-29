abstract class StorageBackend {
  String? getItem(String key);
  void setItem(String key, String value);
}
