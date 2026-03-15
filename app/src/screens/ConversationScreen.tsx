import * as ImagePicker from 'expo-image-picker';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActionSheetIOS,
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { sendMessage, streamMessages, uploadImage } from '../api/client';
import { updateConversationTitle } from '../store/conversations';
import { RootStackParamList } from '../../App';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Conversation'>;
  route: RouteProp<RootStackParamList, 'Conversation'>;
};

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  imageUris?: string[];   // local URIs for display
  pending?: boolean;
}

export default function ConversationScreen({ navigation, route }: Props) {
  const { conversationId } = route.params;
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [pendingImages, setPendingImages] = useState<{ uri: string; mimeType: string }[]>([]);
  const [sending, setSending] = useState(false);
  const listRef = useRef<FlatList>(null);
  const cancelStreamRef = useRef<(() => void) | null>(null);

  // scroll to bottom on new messages
  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
    }
  }, [messages.length]);

  // cleanup stream on unmount
  useEffect(() => {
    return () => {
      cancelStreamRef.current?.();
    };
  }, []);

  async function pickImages(fromCamera: boolean) {
    let result: ImagePicker.ImagePickerResult;

    if (fromCamera) {
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('Permission required', 'Camera access is needed to take photos.');
        return;
      }
      result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.85,
      });
    } else {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('Permission required', 'Photo library access is needed.');
        return;
      }
      result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsMultipleSelection: true,
        quality: 0.85,
      });
    }

    if (result.canceled) return;

    const newImages = result.assets.map((a) => ({
      uri: a.uri,
      mimeType: a.mimeType ?? 'image/jpeg',
    }));
    setPendingImages((prev) => [...prev, ...newImages]);
  }

  function showImagePicker() {
    if (Platform.OS === 'ios') {
      ActionSheetIOS.showActionSheetWithOptions(
        { options: ['Cancel', 'Take Photo', 'Choose from Library'], cancelButtonIndex: 0 },
        (idx) => {
          if (idx === 1) pickImages(true);
          if (idx === 2) pickImages(false);
        }
      );
    } else {
      Alert.alert('Add Image', 'Choose source', [
        { text: 'Camera', onPress: () => pickImages(true) },
        { text: 'Gallery', onPress: () => pickImages(false) },
        { text: 'Cancel', style: 'cancel' },
      ]);
    }
  }

  async function handleSend() {
    const text = input.trim();
    if (!text && pendingImages.length === 0) return;
    if (sending) return;

    setSending(true);
    const localImageUris = pendingImages.map((p) => p.uri);
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      imageUris: localImageUris,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setPendingImages([]);

    try {
      // Upload images in parallel
      const imageUrls = await Promise.all(
        pendingImages.map((p) => uploadImage(p.uri, p.mimeType))
      );

      const { assistantMessageId } = await sendMessage(conversationId, text, imageUrls);

      // Add placeholder for assistant response
      const assistantMsg: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        pending: true,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Stream the response
      cancelStreamRef.current = streamMessages(
        conversationId,
        assistantMessageId,
        (token) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMessageId
                ? { ...m, content: m.content + token }
                : m
            )
          );
        },
        () => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMessageId ? { ...m, pending: false } : m
            )
          );
          setSending(false);
          // Update conversation title with first user message
          if (messages.length === 0 && text) {
            const title = text.slice(0, 40) + (text.length > 40 ? '…' : '');
            updateConversationTitle(conversationId, title);
            navigation.setOptions({ title });
          }
        },
        (err) => {
          Alert.alert('Stream error', err.message);
          setSending(false);
        }
      );
    } catch (e: any) {
      Alert.alert('Error', e.message ?? 'Failed to send message');
      setSending(false);
    }
  }

  const renderMessage = useCallback(({ item }: { item: Message }) => {
    const isUser = item.role === 'user';
    return (
      <View style={[styles.msgRow, isUser ? styles.msgRowUser : styles.msgRowAssistant]}>
        {!isUser && (
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>🤖</Text>
          </View>
        )}
        <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAssistant]}>
          {item.imageUris && item.imageUris.length > 0 && (
            <ScrollView horizontal style={styles.imageRow} showsHorizontalScrollIndicator={false}>
              {item.imageUris.map((uri, i) => (
                <Image key={i} source={{ uri }} style={styles.msgImage} />
              ))}
            </ScrollView>
          )}
          {item.content.length > 0 ? (
            <Text style={[styles.msgText, isUser ? styles.msgTextUser : styles.msgTextAssistant]}>
              {item.content}
            </Text>
          ) : item.pending ? (
            <ActivityIndicator size="small" color="#2563eb" />
          ) : null}
        </View>
      </View>
    );
  }, []);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(m) => m.id}
        renderItem={renderMessage}
        contentContainerStyle={styles.messageList}
        ListEmptyComponent={
          <View style={styles.emptyChat}>
            <Text style={styles.emptyChatText}>Send a message to start learning French!</Text>
          </View>
        }
      />

      {/* Pending image previews */}
      {pendingImages.length > 0 && (
        <View style={styles.pendingImages}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {pendingImages.map((img, i) => (
              <View key={i} style={styles.pendingImageContainer}>
                <Image source={{ uri: img.uri }} style={styles.pendingImage} />
                <TouchableOpacity
                  style={styles.removeImage}
                  onPress={() => setPendingImages((prev) => prev.filter((_, idx) => idx !== i))}
                >
                  <Text style={styles.removeImageText}>✕</Text>
                </TouchableOpacity>
              </View>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Input bar */}
      <View style={styles.inputBar}>
        <TouchableOpacity style={styles.attachBtn} onPress={showImagePicker} disabled={sending}>
          <Text style={styles.attachIcon}>📎</Text>
        </TouchableOpacity>
        <TextInput
          style={styles.textInput}
          value={input}
          onChangeText={setInput}
          placeholder="Type a message…"
          multiline
          maxLength={2000}
          editable={!sending}
        />
        <TouchableOpacity
          style={[styles.sendBtn, (!input.trim() && pendingImages.length === 0) && styles.sendBtnDisabled]}
          onPress={handleSend}
          disabled={sending || (!input.trim() && pendingImages.length === 0)}
        >
          {sending ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.sendIcon}>↑</Text>
          )}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  messageList: { padding: 12, paddingBottom: 8 },
  emptyChat: {
    flex: 1,
    alignItems: 'center',
    paddingTop: 60,
    paddingHorizontal: 40,
  },
  emptyChatText: {
    fontSize: 15,
    color: '#aaa',
    textAlign: 'center',
    lineHeight: 22,
  },

  // Messages
  msgRow: {
    flexDirection: 'row',
    marginVertical: 4,
    alignItems: 'flex-end',
  },
  msgRowUser: { justifyContent: 'flex-end' },
  msgRowAssistant: { justifyContent: 'flex-start' },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#eff6ff',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
    marginBottom: 2,
  },
  avatarText: { fontSize: 16 },
  bubble: {
    maxWidth: '78%',
    borderRadius: 18,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  bubbleUser: {
    backgroundColor: '#2563eb',
    borderBottomRightRadius: 4,
  },
  bubbleAssistant: {
    backgroundColor: '#fff',
    borderBottomLeftRadius: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 1,
  },
  msgText: { fontSize: 15, lineHeight: 22 },
  msgTextUser: { color: '#fff' },
  msgTextAssistant: { color: '#111' },
  imageRow: { marginBottom: 6 },
  msgImage: {
    width: 160,
    height: 120,
    borderRadius: 10,
    marginRight: 6,
  },

  // Pending images
  pendingImages: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  pendingImageContainer: {
    position: 'relative',
    marginRight: 8,
  },
  pendingImage: {
    width: 64,
    height: 64,
    borderRadius: 8,
  },
  removeImage: {
    position: 'absolute',
    top: -4,
    right: -4,
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#333',
    alignItems: 'center',
    justifyContent: 'center',
  },
  removeImageText: { color: '#fff', fontSize: 10, fontWeight: '700' },

  // Input bar
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: 10,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  attachBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 6,
    marginBottom: 1,
  },
  attachIcon: { fontSize: 22 },
  textInput: {
    flex: 1,
    minHeight: 38,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    fontSize: 15,
    color: '#111',
    backgroundColor: '#fafafa',
  },
  sendBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#2563eb',
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 6,
    marginBottom: 1,
  },
  sendBtnDisabled: { backgroundColor: '#93c5fd' },
  sendIcon: { color: '#fff', fontSize: 18, fontWeight: '700' },
});
