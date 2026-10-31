// @ts-ignore -- Node 24 provides this module; the app has no Node type declarations.
import { test } from 'node:test';
// @ts-ignore -- Node 24 provides this module; no extra dependency is needed to run it.
import assert from 'node:assert/strict';

// @ts-ignore -- Node's native TypeScript runner requires the .ts extension.
import { historyToSend, MAX_HISTORY, type ChatMessage } from './assistant.ts';

const turn = (i: number): ChatMessage[] => [
  { role: 'user', content: `soru ${i}` },
  { role: 'assistant', content: `yanıt ${i}` },
];

test('historyToSend kısa konuşmayı olduğu gibi gönderir', () => {
  const messages = [...turn(1), { role: 'user' as const, content: 'soru 2' }];
  assert.deepEqual(historyToSend(messages), messages);
});

test('historyToSend sınırı aşınca son mesajları müşteri mesajıyla başlatır', () => {
  const messages = [...Array.from({ length: 15 }, (_, i) => turn(i)).flat()];
  messages.push({ role: 'user', content: 'son soru' });
  const sent = historyToSend(messages);
  assert.ok(sent.length <= MAX_HISTORY);
  assert.equal(sent[0].role, 'user');
  assert.equal(sent.at(-1)?.content, 'son soru');
});

test('historyToSend müşteri mesajı yoksa boş döner', () => {
  assert.deepEqual(historyToSend([{ role: 'assistant', content: 'merhaba' }]), []);
});
