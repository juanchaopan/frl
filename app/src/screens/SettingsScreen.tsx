import React, { useEffect, useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { getServerUrl, setServerUrl } from '../store/settings';

export default function SettingsScreen() {
  const [url, setUrl] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getServerUrl().then(setUrl);
  }, []);

  async function handleSave() {
    const trimmed = url.trim();
    if (!trimmed) {
      Alert.alert('Error', 'Server URL cannot be empty.');
      return;
    }
    try {
      new URL(trimmed);
    } catch {
      Alert.alert('Error', 'Please enter a valid URL (e.g. http://192.168.1.10:8000)');
      return;
    }
    await setServerUrl(trimmed);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <Text style={styles.label}>Server Address</Text>
      <TextInput
        style={styles.input}
        value={url}
        onChangeText={(t) => { setUrl(t); setSaved(false); }}
        placeholder="http://192.168.1.10:8000"
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
      />
      <Text style={styles.hint}>
        The base URL of your FRL server (no trailing slash).
      </Text>
      <TouchableOpacity style={styles.button} onPress={handleSave}>
        <Text style={styles.buttonText}>{saved ? 'Saved ✓' : 'Save'}</Text>
      </TouchableOpacity>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    backgroundColor: '#fff',
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#555',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: '#111',
    backgroundColor: '#fafafa',
  },
  hint: {
    marginTop: 8,
    fontSize: 12,
    color: '#999',
  },
  button: {
    marginTop: 24,
    backgroundColor: '#2563eb',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
