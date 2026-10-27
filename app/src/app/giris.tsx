import { router } from 'expo-router';
import { useState } from 'react';
import {
  AccessibilityInfo,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Logo } from '@/components/brand/logo';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Button } from '@/components/ui/button';
import { TextField } from '@/components/ui/text-field';
import { MaxContentWidth, Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { checkDemoCredentials, DEMO_CREDENTIALS } from '@/lib/demo-account';
import { signIn } from '@/lib/session';
import { digitsOnly, validateLogin, type LoginErrors } from '@/lib/validation';

export default function LoginScreen() {
  const theme = useTheme();
  const [customerNo, setCustomerNo] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<LoginErrors>({});
  const [formError, setFormError] = useState<string | null>(null);

  function submit() {
    const next = validateLogin(customerNo, password);
    setErrors(next);
    setFormError(null);
    // accessibilityLiveRegion only covers Android; announce explicitly so VoiceOver hears it too.
    const firstError = next.customerNo ?? next.password;
    if (firstError) {
      AccessibilityInfo.announceForAccessibility(firstError);
      return;
    }
    // Until the FastAPI backend exists, only the demo account can sign in.
    const customer = checkDemoCredentials(customerNo, password);
    if (!customer) {
      const message = 'Müşteri numarası veya şifre hatalı.';
      setFormError(message);
      AccessibilityInfo.announceForAccessibility(message);
      return;
    }
    signIn(customer);
    router.replace('/hesabim');
  }

  function fillDemo() {
    setCustomerNo(DEMO_CREDENTIALS.customerNo);
    setPassword(DEMO_CREDENTIALS.password);
    setErrors({});
    setFormError(null);
  }

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
            <View style={styles.header}>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Geri"
                hitSlop={12}
                onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))}>
                <ThemedText type="label">← Geri</ThemedText>
              </Pressable>
              <Logo variant="horizontal" size={32} />
            </View>

            <View style={styles.copy}>
              <ThemedText type="title">Tekrar hoş geldiniz</ThemedText>
              <ThemedText themeColor="textSecondary">
                Müşteri numaranız ve 6 haneli şifrenizle giriş yapın.
              </ThemedText>
            </View>

            <View style={styles.form}>
              <TextField
                label="Müşteri numarası"
                placeholder="123456789"
                value={customerNo}
                onChangeText={(v) => setCustomerNo(digitsOnly(v, 9))}
                keyboardType="number-pad"
                autoComplete="username"
                textContentType="username"
                returnKeyType="next"
                error={errors.customerNo}
              />
              <TextField
                label="Şifre"
                placeholder="••••••"
                value={password}
                onChangeText={(v) => setPassword(digitsOnly(v, 6))}
                keyboardType="number-pad"
                secureTextEntry
                autoComplete="current-password"
                textContentType="password"
                returnKeyType="go"
                onSubmitEditing={submit}
                error={errors.password}
              />
            </View>

            {formError ? (
              <View
                style={[styles.notice, { backgroundColor: theme.backgroundElement, borderLeftColor: theme.danger }]}
                accessibilityLiveRegion="polite">
                <ThemedText type="small">{formError}</ThemedText>
              </View>
            ) : null}

            <Button title="Giriş yap" onPress={submit} />

            <View
              style={[styles.notice, { backgroundColor: theme.backgroundElement, borderLeftColor: theme.accent }]}>
              <ThemedText type="smallBold">Demo hesap</ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                Müşteri no: {DEMO_CREDENTIALS.customerNo} · Şifre: {DEMO_CREDENTIALS.password}
              </ThemedText>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Demo hesap bilgilerini doldur"
                hitSlop={8}
                onPress={fillDemo}
                style={styles.fillDemo}>
                <ThemedText type="link">Bilgileri doldur</ThemedText>
              </Pressable>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </ThemedView>
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
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.four,
    gap: Spacing.five,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  copy: {
    gap: Spacing.two,
  },
  form: {
    gap: Spacing.four,
  },
  notice: {
    borderRadius: Radius.card,
    borderLeftWidth: 4,
    padding: Spacing.three,
    gap: Spacing.one,
  },
  fillDemo: {
    alignSelf: 'flex-start',
    marginTop: Spacing.one,
  },
});
