import { Redirect, router } from 'expo-router';
import { useState } from 'react';
import { AccessibilityInfo, ActivityIndicator, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Button } from '@/components/ui/button';
import { Notice } from '@/components/ui/notice';
import { Screen } from '@/components/ui/screen';
import { ScreenHeader } from '@/components/ui/screen-header';
import { TextField } from '@/components/ui/text-field';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { ApiError, changePassword } from '@/lib/api';
import { signOut, useSession } from '@/lib/session';
import {
  digitsOnly,
  validateChangePassword,
  type ChangePasswordErrors,
  type ChangePasswordFields,
} from '@/lib/validation';

const EMPTY: ChangePasswordFields = { current: '', password: '', passwordRepeat: '' };

export default function ChangePasswordScreen() {
  const theme = useTheme();
  const session = useSession();
  const [fields, setFields] = useState<ChangePasswordFields>(EMPTY);
  const [errors, setErrors] = useState<ChangePasswordErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  if (session.status === 'unknown') {
    return (
      <ThemedView style={styles.loading}>
        <ActivityIndicator color={theme.primary} accessibilityLabel="Yükleniyor" />
      </ThemedView>
    );
  }
  if (session.status === 'signedOut') return <Redirect href="/giris" />;

  function update(key: keyof ChangePasswordFields, value: string) {
    setFields((f) => ({ ...f, [key]: digitsOnly(value, 6) }));
    setErrors((e) => ({ ...e, [key]: undefined }));
  }

  async function submit() {
    if (submitting) return;
    const next = validateChangePassword(fields);
    setErrors(next);
    setFormError(null);
    const first = next.current ?? next.password ?? next.passwordRepeat;
    if (first) {
      AccessibilityInfo.announceForAccessibility(first);
      return;
    }
    setSubmitting(true);
    try {
      await changePassword(fields.current, fields.password);
      setFields(EMPTY);
      setDone(true);
      AccessibilityInfo.announceForAccessibility('Şifreniz değiştirildi.');
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return void signOut();
      const message =
        e instanceof ApiError && e.status === 0
          ? 'Bağlantı kesildi. Şifreniz değişmiş olabilir; yeni şifrenizle giriş yapmayı deneyin.'
          : e instanceof ApiError
            ? e.message
            : 'Beklenmeyen bir hata oluştu.';
      // A wrong current password is about that field; everything else is about the form.
      if (e instanceof ApiError && e.message === 'Mevcut şifreniz hatalı.')
        setErrors({ current: message });
      else setFormError(message);
      AccessibilityInfo.announceForAccessibility(message);
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <Screen>
        <View style={styles.copy}>
          <ThemedText type="title">Şifreniz değiştirildi</ThemedText>
          <ThemedText themeColor="textSecondary">
            Bundan sonra yeni şifrenizle giriş yapın. Güvenliğiniz için diğer cihazlardaki
            oturumlarınız kapatıldı.
          </ThemedText>
        </View>
        <Button title="Hesabıma dön" onPress={() => router.replace('/hesabim')} />
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader fallback="/hesabim" />
      <View style={styles.copy}>
        <ThemedText type="title">Şifre değiştir</ThemedText>
        <ThemedText themeColor="textSecondary">
          Yeni şifreniz 6 haneli olmalı. Şifreyi değiştirdiğinizde diğer cihazlardaki oturumlarınız
          kapanır.
        </ThemedText>
      </View>

      {formError ? (
        <Notice tone="error">
          <ThemedText type="small">{formError}</ThemedText>
        </Notice>
      ) : null}

      <View style={styles.form}>
        <TextField
          label="Mevcut şifre"
          placeholder="••••••"
          value={fields.current}
          onChangeText={(v) => update('current', v)}
          keyboardType="number-pad"
          secureTextEntry
          autoComplete="current-password"
          textContentType="password"
          error={errors.current}
        />
        <TextField
          label="Yeni şifre"
          placeholder="••••••"
          value={fields.password}
          onChangeText={(v) => update('password', v)}
          keyboardType="number-pad"
          secureTextEntry
          autoComplete="new-password"
          textContentType="newPassword"
          error={errors.password}
        />
        <TextField
          label="Yeni şifre (tekrar)"
          placeholder="••••••"
          value={fields.passwordRepeat}
          onChangeText={(v) => update('passwordRepeat', v)}
          keyboardType="number-pad"
          secureTextEntry
          autoComplete="new-password"
          textContentType="newPassword"
          returnKeyType="go"
          onSubmitEditing={submit}
          error={errors.passwordRepeat}
        />
      </View>

      <Button title="Şifreyi değiştir" onPress={submit} loading={submitting} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  copy: {
    gap: Spacing.two,
  },
  form: {
    gap: Spacing.four,
  },
});
