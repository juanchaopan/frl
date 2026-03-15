import AsyncStorage from '@react-native-async-storage/async-storage';

const SERVER_URL_KEY = 'server_url';
const DEFAULT_SERVER_URL = 'http://localhost:8000';

export async function getServerUrl(): Promise<string> {
  const url = await AsyncStorage.getItem(SERVER_URL_KEY);
  return url ?? DEFAULT_SERVER_URL;
}

export async function setServerUrl(url: string): Promise<void> {
  await AsyncStorage.setItem(SERVER_URL_KEY, url.replace(/\/$/, ''));
}
