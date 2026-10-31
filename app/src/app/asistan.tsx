import { Redirect } from 'expo-router';
import { useRef, useState } from 'react';
import {
  AccessibilityInfo,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
  type ScrollViewInstance,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Button } from '@/components/ui/button';
import { Notice } from '@/components/ui/notice';
import { ScreenHeader } from '@/components/ui/screen-header';
import { Fonts, MaxContentWidth, Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { ApiError, askAssistant } from '@/lib/api';
import { historyToSend, MAX_MESSAGE_LENGTH, type ChatMessage } from '@/lib/assistant';
import { signOut, useSession } from '@/lib/session';

const SUGGESTIONS = ['Toplam bakiyem ne kadar?', 'Son harcamalarım neler?', 'Kredi borcum ne kadar?'];

export default function AssistantScreen() {
  const theme = useTheme();
  const session = useSession();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scroll = useRef<ScrollViewInstance>(null);

  if (session.status === 'signedOut') return <Redirect href="/giris" />;

  async function send(text: string) {
    const question = text.trim();
    if (sending || !question) return;
    const next: ChatMessage[] = [...messages, { role: 'user', content: question }];
    setMessages(next);
    setInput('');
    setError(null);
    setSending(true);
    try {
      const reply = await askAssistant(historyToSend(next));
      setMessages([...next, { role: 'assistant', content: reply }]);
      AccessibilityInfo.announceForAccessibility(reply);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return void signOut();
      // Give the question back so it can be sent again; it never reached the history. Keep
      // anything typed while waiting rather than overwriting it.
      setMessages(messages);
      setInput((current) => (current.trim() ? current : question));
      const message = e instanceof ApiError ? e.message : 'Beklenmeyen bir hata oluştu.';
      setError(message);
      AccessibilityInfo.announceForAccessibility(message);
    } finally {
      setSending(false);
    }
  }

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView
            ref={scroll}
            contentContainerStyle={styles.scroll}
            keyboardShouldPersistTaps="handled"
            onContentSizeChange={() => scroll.current?.scrollToEnd({ animated: true })}>
            <ScreenHeader fallback="/hesabim" />
            <View style={styles.copy}>
              <ThemedText type="title">Asistan</ThemedText>
              <ThemedText themeColor="textSecondary">
                Hesaplarınız ve hareketleriniz hakkında soru sorun. Asistan yalnızca bilgilerinizi
                okur; para gönderemez veya işlem yapamaz. Yapay zekâ ile çalışır, hata yapabilir.
              </ThemedText>
            </View>

            {messages.length === 0 ? (
              <View style={styles.suggestions}>
                {SUGGESTIONS.map((s) => (
                  <Button key={s} title={s} variant="secondary" onPress={() => send(s)} />
                ))}
              </View>
            ) : null}

            <View style={styles.messages} accessibilityLiveRegion="polite">
              {messages.map((m, i) => (
                <Bubble key={i} message={m} />
              ))}
              {sending ? (
                <View style={[styles.bubble, { backgroundColor: theme.backgroundElement }]}>
                  <ActivityIndicator color={theme.primary} accessibilityLabel="Asistan yazıyor" />
                </View>
              ) : null}
            </View>

            {error ? (
              <Notice tone="error">
                <ThemedText type="small">{error}</ThemedText>
              </Notice>
            ) : null}
          </ScrollView>

          <View style={[styles.composer, { borderTopColor: theme.border }]}>
            <TextInput
              value={input}
              onChangeText={setInput}
              placeholder="Bir soru yazın"
              placeholderTextColor={theme.textSecondary}
              maxLength={MAX_MESSAGE_LENGTH}
              multiline
              accessibilityLabel="Asistana mesaj"
              style={[
                styles.input,
                { color: theme.text, backgroundColor: theme.backgroundElement, borderColor: theme.border },
              ]}
            />
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Gönder"
              accessibilityState={{ disabled: sending || !input.trim() }}
              disabled={sending || !input.trim()}
              onPress={() => send(input)}
              style={({ pressed }) => [
                styles.send,
                { backgroundColor: theme.primary },
                (sending || !input.trim()) && styles.disabled,
                pressed && styles.pressed,
              ]}>
              <ThemedText type="smallBold" themeColor="onPrimary">
                Gönder
              </ThemedText>
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </ThemedView>
  );
}

function Bubble({ message }: { message: ChatMessage }) {
  const theme = useTheme();
  const mine = message.role === 'user';
  return (
    <View
      accessibilityLabel={`${mine ? 'Siz' : 'Asistan'}: ${message.content}`}
      style={[
        styles.bubble,
        mine
          ? [styles.mine, { backgroundColor: theme.primary }]
          : { backgroundColor: theme.backgroundElement },
      ]}>
      <ThemedText themeColor={mine ? 'onPrimary' : 'text'} selectable>
        {message.content}
      </ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  container: {
    flex: 1,
    alignItems: 'center',
  },
  safeArea: {
    flex: 1,
    width: '100%',
    maxWidth: MaxContentWidth,
  },
  scroll: {
    flexGrow: 1,
    padding: Spacing.four,
    gap: Spacing.four,
  },
  copy: {
    gap: Spacing.two,
  },
  suggestions: {
    gap: Spacing.two,
  },
  messages: {
    gap: Spacing.three,
  },
  bubble: {
    alignSelf: 'flex-start',
    maxWidth: '85%',
    borderRadius: Radius.card,
    paddingVertical: Spacing.two,
    paddingHorizontal: Spacing.three,
  },
  mine: {
    alignSelf: 'flex-end',
  },
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Spacing.two,
    padding: Spacing.three,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  input: {
    flex: 1,
    minHeight: 48,
    maxHeight: 140,
    borderWidth: 1,
    borderRadius: Radius.card,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    fontFamily: Fonts.regular,
    fontSize: 16,
  },
  send: {
    minHeight: 48,
    justifyContent: 'center',
    borderRadius: Radius.card,
    paddingHorizontal: Spacing.three,
  },
  disabled: {
    opacity: 0.5,
  },
  pressed: {
    opacity: 0.85,
  },
});
