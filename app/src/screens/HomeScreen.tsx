import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { createConversation } from '../api/client';
import {
  ConversationMeta,
  addConversation,
  getConversations,
  removeConversation,
} from '../store/conversations';
import { RootStackParamList } from '../../App';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Home'>;
};

export default function HomeScreen({ navigation }: Props) {
  const [conversations, setConversations] = useState<ConversationMeta[]>([]);
  const [creating, setCreating] = useState(false);

  useFocusEffect(
    useCallback(() => {
      getConversations().then(setConversations);
    }, [])
  );

  async function handleNew() {
    setCreating(true);
    try {
      const id = await createConversation();
      const meta: ConversationMeta = {
        id,
        title: 'New conversation',
        createdAt: new Date().toISOString(),
      };
      await addConversation(meta);
      setConversations((prev) => [meta, ...prev]);
      navigation.navigate('Conversation', { conversationId: id });
    } catch (e: any) {
      Alert.alert('Error', e.message ?? 'Could not create conversation');
    } finally {
      setCreating(false);
    }
  }

  function handleDelete(id: string) {
    Alert.alert('Delete', 'Remove this conversation?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          await removeConversation(id);
          setConversations((prev) => prev.filter((c) => c.id !== id));
        },
      },
    ]);
  }

  function formatDate(iso: string) {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={conversations}
        keyExtractor={(item) => item.id}
        contentContainerStyle={conversations.length === 0 ? styles.emptyList : styles.list}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>💬</Text>
            <Text style={styles.emptyText}>No conversations yet</Text>
            <Text style={styles.emptySubtext}>Tap + to start a new one</Text>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.row}
            onPress={() => navigation.navigate('Conversation', { conversationId: item.id })}
            onLongPress={() => handleDelete(item.id)}
          >
            <View style={styles.rowIcon}>
              <Text style={styles.rowIconText}>💬</Text>
            </View>
            <View style={styles.rowContent}>
              <Text style={styles.rowTitle} numberOfLines={1}>{item.title}</Text>
              <Text style={styles.rowDate}>{formatDate(item.createdAt)}</Text>
            </View>
            <Text style={styles.rowChevron}>›</Text>
          </TouchableOpacity>
        )}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
      />

      <TouchableOpacity
        style={[styles.fab, creating && styles.fabDisabled]}
        onPress={handleNew}
        disabled={creating}
      >
        {creating ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.fabText}>+</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  list: { paddingVertical: 8 },
  emptyList: { flex: 1 },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingBottom: 80,
  },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { fontSize: 18, fontWeight: '600', color: '#333' },
  emptySubtext: { fontSize: 14, color: '#999', marginTop: 4 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  rowIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#eff6ff',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  rowIconText: { fontSize: 20 },
  rowContent: { flex: 1 },
  rowTitle: { fontSize: 16, fontWeight: '500', color: '#111' },
  rowDate: { fontSize: 12, color: '#999', marginTop: 2 },
  rowChevron: { fontSize: 22, color: '#ccc', marginLeft: 8 },
  separator: { height: 1, backgroundColor: '#f0f0f0', marginLeft: 68 },
  fab: {
    position: 'absolute',
    right: 20,
    bottom: 30,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#2563eb',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#2563eb',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 6,
  },
  fabDisabled: { opacity: 0.6 },
  fabText: { color: '#fff', fontSize: 28, fontWeight: '300', lineHeight: 32 },
});
