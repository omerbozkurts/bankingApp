import { Redirect, router } from 'expo-router';
import { useState } from 'react';
import { AccessibilityInfo, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { Button } from '@/components/ui/button';
import { ChoiceList } from '@/components/ui/choice-list';
import { Notice } from '@/components/ui/notice';
import { Screen } from '@/components/ui/screen';
import { ScreenHeader } from '@/components/ui/screen-header';
import { TextField } from '@/components/ui/text-field';
import { Spacing } from '@/constants/theme';
import { ApiError, openAccount } from '@/lib/api';
import type { AccountKind } from '@/lib/models';
import { formatKurus, parseTryAmount } from '@/lib/money';
import { refreshCustomer, signOut, useSession } from '@/lib/session';

const DEFAULT_NAMES: Record<AccountKind, string> = {
  checking: 'Vadesiz TL Hesabı',
  savings: 'Birikim Hesabı',
};

export default function OpenAccountScreen() {
  const session = useSession();
  const [kind, setKind] = useState<AccountKind>('savings');
  const [name, setName] = useState('');
  const [goalInput, setGoalInput] = useState('');
  const [errors, setErrors] = useState<{ name?: string; goal?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (session.status === 'signedOut') return <Redirect href="/giris" />;

  const goalKurus = goalInput.trim() ? parseTryAmount(goalInput) : null;

  async function submit() {
    if (submitting) return;
    const next: typeof errors = {};
    const finalName = name.trim() || DEFAULT_NAMES[kind];
    if (finalName.length > 80) next.name = 'Hesap adı en fazla 80 karakter olabilir.';
    if (kind === 'savings' && goalInput.trim() && goalKurus === null)
      next.goal = 'Hedefi 25.000 biçiminde girin.';
    setErrors(next);
    setFormError(null);
    const first = Object.values(next)[0];
    if (first) {
      AccessibilityInfo.announceForAccessibility(first);
      return;
    }

    setSubmitting(true);
    try {
      await openAccount({ kind, name: finalName, goalKurus: kind === 'savings' ? goalKurus : null });
      await refreshCustomer();
      AccessibilityInfo.announceForAccessibility(`${finalName} açıldı.`);
      router.replace('/hesabim');
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return void signOut();
      const message = e instanceof ApiError ? e.message : 'Beklenmeyen bir hata oluştu.';
      setFormError(message);
      AccessibilityInfo.announceForAccessibility(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader fallback="/hesabim" />
      <View style={styles.copy}>
        <ThemedText type="title">Yeni hesap</ThemedText>
        <ThemedText themeColor="textSecondary">
          Birikim hesabına bir hedef koyun; her katman sizi hedefe yaklaştırır.
        </ThemedText>
      </View>

      <View style={styles.form}>
        <ChoiceList<AccountKind>
          label="Hesap türü"
          value={kind}
          onChange={(k) => {
            setKind(k);
            setErrors({});
          }}
          choices={[
            { value: 'savings', title: 'Birikim hesabı', detail: 'Hedef belirleyin, ilerlemenizi görün' },
            { value: 'checking', title: 'Vadesiz hesap', detail: 'Günlük harcama ve transferler için' },
          ]}
        />
        <TextField
          label="Hesap adı (isteğe bağlı)"
          placeholder={DEFAULT_NAMES[kind]}
          value={name}
          onChangeText={setName}
          maxLength={80}
          error={errors.name}
        />
        {kind === 'savings' ? (
          <View style={styles.field}>
            <TextField
              label="Birikim hedefi (TL, isteğe bağlı)"
              placeholder="25.000"
              value={goalInput}
              onChangeText={(v) => setGoalInput(v.replace(/[^\d.,]/g, '').slice(0, 18))}
              keyboardType="decimal-pad"
              error={errors.goal}
            />
            {goalKurus !== null && !errors.goal ? (
              <ThemedText type="small" themeColor="textSecondary">
                Hedef: {formatKurus(goalKurus)}
              </ThemedText>
            ) : null}
          </View>
        ) : null}
      </View>

      {formError ? (
        <Notice tone="error">
          <ThemedText type="small">{formError}</ThemedText>
        </Notice>
      ) : null}

      <Button title="Hesabı aç" onPress={submit} loading={submitting} />
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
  field: {
    gap: Spacing.one,
  },
});
