import AsyncStorage from '@react-native-async-storage/async-storage';

const CONVERSATIONS_KEY = 'conversations';

export interface ConversationMeta {
  id: string;
  title: string;
  createdAt: string;
}

export async function getConversations(): Promise<ConversationMeta[]> {
  const raw = await AsyncStorage.getItem(CONVERSATIONS_KEY);
  return raw ? JSON.parse(raw) : [];
}

export async function addConversation(conv: ConversationMeta): Promise<void> {
  const list = await getConversations();
  list.unshift(conv);
  await AsyncStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(list));
}

export async function removeConversation(id: string): Promise<void> {
  const list = await getConversations();
  await AsyncStorage.setItem(
    CONVERSATIONS_KEY,
    JSON.stringify(list.filter((c) => c.id !== id))
  );
}

export async function updateConversationTitle(id: string, title: string): Promise<void> {
  const list = await getConversations();
  const idx = list.findIndex((c) => c.id === id);
  if (idx !== -1) {
    list[idx].title = title;
    await AsyncStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(list));
  }
}
