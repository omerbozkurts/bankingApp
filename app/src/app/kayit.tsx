import { router } from 'expo-router';
import { useState } from 'react';
import { AccessibilityInfo, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Button } from '@/components/ui/button';
import { Notice } from '@/components/ui/notice';
import { Screen } from '@/components/ui/screen';
import { ScreenHeader } from '@/components/ui/screen-header';
import { TextField } from '@/components/ui/text-field';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { ApiError, register } from '@/lib/api';
import {
  digitsOnly,
  formatDateInput,
  parseTrDate,
  validateRegister,
  type RegisterErrors,
  type RegisterFields,
} from '@/lib/validation';

const EMPTY: RegisterFields = {
  nationalId: '',
  fullName: '',
  birthDate: '',
  password: '',
  passwordRepeat: '',
};

export default function RegisterScreen() {
  const theme = useTheme();
  const [fields, setFields] = useState<RegisterFields>(EMPTY);
  const [errors, setErrors] = useState<RegisterErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState<{ customerNo: string; fullName: string } | null>(null);

  const update = (key: keyof RegisterFields) => (value: string) =>
    setFields((f) => ({ ...f, [key]: value }));

  async function submit() {
    if (submitting) return;
    const next = validateRegister(fields);
    setErrors(next);
    setFormError(null);
    const first = Object.values(next)[0];
    if (first) {
      AccessibilityInfo.announceForAccessibility(first);
      return;
    }
    setSubmitting(true);
    try {
      const result = await register({
        nationalId: fields.nationalId,
        fullName: fields.fullName.trim().replace(/\s+/g, ' '),
        birthDate: parseTrDate(fields.birthDate)!,
        password: fields.password,
      });
      setCreated(result);
      setFields(EMPTY);
      AccessibilityInfo.announceForAccessibility(
        `Kaydınız tamamlandı. Müşteri numaranız ${result.customerNo.split('').join(' ')}.`,
      );
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Beklenmeyen bir hata oluştu.';
      setFormError(message);
      AccessibilityInfo.announceForAccessibility(message);
    } finally {
      setSubmitting(false);
    }
  }

  if (created) {
    return (
      <Screen>
        <View style={styles.copy}>
          <ThemedText type="title">Hoş geldiniz, {created.fullName.split(' ')[0]}</ThemedText>
          <ThemedText themeColor="textSecondary">
            Hesabınız açıldı. Giriş yaparken bu müşteri numarasını kullanacaksınız; bir yere not edin.
          </ThemedText>
        </View>
        <View style={[styles.customerNo, { backgroundColor: theme.backgroundElement }]}>
          <ThemedText type="label" themeColor="textSecondary">
            Müşteri numaranız
          </ThemedText>
          <ThemedText type="title" selectable style={styles.digits}>
            {created.customerNo}
          </ThemedText>
        </View>
        <Button
          title="Giriş yap"
          onPress={() =>
            router.replace({ pathname: '/giris', params: { musteriNo: created.customerNo } })
          }
        />
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader fallback="/" />
      <View style={styles.copy}>
        <ThemedText type="title">Hesap açın</ThemedText>
        <ThemedText themeColor="textSecondary">
          Birkaç bilgiyle vadesiz hesabınız hemen açılır.
        </ThemedText>
      </View>

      <View style={styles.form}>
        <TextField
          label="T.C. kimlik numarası"
          value={fields.nationalId}
          onChangeText={(v) => update('nationalId')(digitsOnly(v, 11))}
          keyboardType="number-pad"
          autoComplete="off"
          error={errors.nationalId}
        />
        <TextField
          label="Ad soyad"
          value={fields.fullName}
          onChangeText={update('fullName')}
          autoComplete="name"
          textContentType="name"
          autoCapitalize="words"
          error={errors.fullName}
        />
        <TextField
          label="Doğum tarihi"
          placeholder="GG.AA.YYYY"
          value={fields.birthDate}
          onChangeText={(v) => update('birthDate')(formatDateInput(v))}
          keyboardType="number-pad"
          autoComplete="birthdate-full"
          error={errors.birthDate}
        />
        <TextField
          label="Şifre (6 hane)"
          value={fields.password}
          onChangeText={(v) => update('password')(digitsOnly(v, 6))}
          keyboardType="number-pad"
          secureTextEntry
          autoComplete="new-password"
          textContentType="newPassword"
          error={errors.password}
        />
        <TextField
          label="Şifre (tekrar)"
          value={fields.passwordRepeat}
          onChangeText={(v) => update('passwordRepeat')(digitsOnly(v, 6))}
          keyboardType="number-pad"
          secureTextEntry
          autoComplete="new-password"
          textContentType="newPassword"
          returnKeyType="go"
          onSubmitEditing={submit}
          error={errors.passwordRepeat}
        />
      </View>

      {formError ? (
        <Notice tone="error">
          <ThemedText type="small">{formError}</ThemedText>
        </Notice>
      ) : null}

      <Button title="Hesabımı aç" onPress={submit} loading={submitting} />
      <ThemedText type="small" themeColor="textSecondary" style={styles.center}>
        Kimlik numaranız açık metin olarak saklanmaz.
      </ThemedText>
    </Screen>
  );
}

const styles = StyleSheet.create({
  copy: {
    gap: Spacing.two,
  },
  form: {
    gap: Spacing.four,
  },
  customerNo: {
    borderRadius: Radius.card,
    padding: Spacing.four,
    gap: Spacing.one,
    alignItems: 'center',
  },
  digits: {
    letterSpacing: 4,
  },
  center: {
    textAlign: 'center',
  },
});
