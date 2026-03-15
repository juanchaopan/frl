import { getServerUrl } from '../store/settings';

async function baseUrl(): Promise<string> {
  return getServerUrl();
}

// ─── Conversations ────────────────────────────────────────────────────────────

export async function createConversation(): Promise<string> {
  const url = await baseUrl();
  const res = await fetch(`${url}/conversations`, { method: 'POST' });
  if (!res.ok) throw new Error(`Create conversation failed: ${res.status}`);
  const data = await res.json();
  return data.id as string;
}

// ─── Messages ─────────────────────────────────────────────────────────────────

export interface SendMessageResult {
  assistantMessageId: string;
}

export async function sendMessage(
  conversationId: string,
  message: string,
  imageUrls: string[]
): Promise<SendMessageResult> {
  const url = await baseUrl();
  const res = await fetch(`${url}/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, image_urls: imageUrls }),
  });
  if (!res.ok) throw new Error(`Send message failed: ${res.status}`);
  const data = await res.json();
  return { assistantMessageId: data.assistant_message_id };
}

// ─── SSE streaming ────────────────────────────────────────────────────────────

export interface SseEvent {
  type: 'content' | 'end';
  content: string;
}

/**
 * Streams assistant response tokens using XMLHttpRequest (onprogress).
 * Calls onToken for each token and onDone when the stream ends.
 * Returns a cancel function.
 */
export function streamMessages(
  conversationId: string,
  fromMessageId: string,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (err: Error) => void
): () => void {
  let cancelled = false;
  let serverUrl = '';

  getServerUrl().then((url) => {
    if (cancelled) return;
    serverUrl = url;

    const xhr = new XMLHttpRequest();
    const endpoint = `${url}/conversations/${conversationId}/messages?from_message_id=${fromMessageId}`;
    xhr.open('GET', endpoint, true);
    xhr.setRequestHeader('Accept', 'text/event-stream');
    xhr.setRequestHeader('Cache-Control', 'no-cache');

    let cursor = 0;

    xhr.onprogress = () => {
      if (cancelled) return;
      const chunk = xhr.responseText.slice(cursor);
      cursor = xhr.responseText.length;

      const lines = chunk.split('\n');
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const event: SseEvent = JSON.parse(line.slice(6));
          if (event.type === 'content') {
            onToken(event.content);
          } else if (event.type === 'end') {
            onDone();
          }
        } catch {
          // ignore malformed lines
        }
      }
    };

    xhr.onerror = () => {
      if (!cancelled) onError(new Error('Stream connection error'));
    };

    xhr.onloadend = () => {
      if (!cancelled) onDone();
    };

    xhr.send();

    // store ref for cancel
    (streamMessages as any)._xhr = xhr;
  });

  return () => {
    cancelled = true;
    if ((streamMessages as any)._xhr) {
      (streamMessages as any)._xhr.abort();
    }
  };
}

// ─── Images ───────────────────────────────────────────────────────────────────

export async function uploadImage(
  uri: string,
  mimeType: string
): Promise<string> {
  const url = await baseUrl();

  const formData = new FormData();
  formData.append('file', {
    uri,
    type: mimeType,
    name: `upload.${mimeType.split('/')[1] ?? 'jpg'}`,
  } as any);

  const res = await fetch(`${url}/images`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Upload failed (${res.status}): ${text}`);
  }

  const data = await res.json();
  return data.url as string;
}
