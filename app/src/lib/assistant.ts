// Mirrors the API's limits (backend/app/schemas.py: AssistantRequest).
export const MAX_MESSAGE_LENGTH = 2000;
export const MAX_HISTORY = 20;

export type ChatMessage = { role: 'user' | 'assistant'; content: string };

/** The latest messages the API accepts: at most MAX_HISTORY, starting with a customer message. */
export function historyToSend(messages: ChatMessage[]): ChatMessage[] {
  const recent = messages.slice(-MAX_HISTORY);
  const start = recent.findIndex((m) => m.role === 'user');
  return start === -1 ? [] : recent.slice(start);
}
