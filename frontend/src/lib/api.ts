import { ChatApiResponse, Conversation, Message } from '@/types';

const getApiBase = () => {
  if (typeof window !== 'undefined') {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://localhost:8001/api';
    }
  }
  return '/api';
};

const API_BASE = getApiBase();

export async function sendChatMessage(
  question: string,
  conversationId?: string
): Promise<ChatApiResponse> {
  const body: Record<string, string> = { question };
  if (conversationId) {
    body.conversation_id = conversationId;
  }

  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Conversation persistence API

export async function fetchConversations(page = 1, pageSize = 50) {
  try {
    const response = await fetch(`${API_BASE}/conversations?page=${page}&page_size=${pageSize}`);
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export async function fetchConversation(id: string) {
  try {
    const response = await fetch(`${API_BASE}/conversations/${id}`);
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export async function saveConversation(conversation: Conversation) {
  try {
    const body = {
      id: conversation.id,
      title: conversation.title,
      created_at: conversation.createdAt,
      updated_at: conversation.updatedAt,
      messages: conversation.messages.map((msg) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        sql_query: msg.sql || null,
        raw_data: msg.rawData || null,
        chart_type: msg.suggestedChartType || null,
        chart_config: msg.chartConfig || null,
        domain: msg.domain || null,
        row_count: msg.rowCount || null,
        created_at: msg.timestamp,
      })),
    };

    const response = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    return response.ok;
  } catch {
    return false;
  }
}

export async function deleteConversationApi(id: string) {
  try {
    const response = await fetch(`${API_BASE}/conversations/${id}`, {
      method: 'DELETE',
    });
    return response.ok || response.status === 204;
  } catch {
    return false;
  }
}
