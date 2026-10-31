import { Redirect } from 'expo-router';
import { useEffect, useState } from 'react';
import { AccessibilityInfo, ActivityIndicator, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Button } from '@/components/ui/button';
import { Notice } from '@/components/ui/notice';
import { Screen } from '@/components/ui/screen';
import { ScreenHeader } from '@/components/ui/screen-header';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { ApiError, deleteSavedRecipient, fetchSavedRecipients } from '@/lib/api';
import { formatIban } from '@/lib/banking';
import type { SavedRecipient } from '@/lib/models';
import { signOut, useSession } from '@/lib/session';

/** The customer's saved recipients; new ones are saved after a transfer (gonder.tsx). */
export default function SavedRecipientsScreen() {
  const theme = useTheme();
  const session = useSession();
  const [rows, setRows] = useState<SavedRecipient[] | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const signedIn = session.status === 'signedIn';
  useEffect(() => {
    if (!signedIn) return;
    let cancelled = false;
    fetchSavedRecipients().then(
      (list) => {
        if (!cancelled) setRows(list);
      },
      (e) => {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) return void signOut();
        setError(e instanceof ApiError ? e.message : 'Alıcılar yüklenemedi.');
        setRows([]);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [signedIn]);

  if (session.status === 'unknown') {
    return (
      <ThemedView style={styles.loading}>
        <ActivityIndicator color={theme.primary} accessibilityLabel="Yükleniyor" />
      </ThemedView>
    );
  }
  if (session.status === 'signedOut') return <Redirect href="/giris" />;

  async function remove(row: SavedRecipient) {
    if (deleting !== null) return;
    setDeleting(row.id);
    setError(null);
    try {
      await deleteSavedRecipient(row.id);
      setRows((list) => list?.filter((r) => r.id !== row.id) ?? null);
      AccessibilityInfo.announceForAccessibility(`${row.nickname} silindi.`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return void signOut();
      // Already gone (e.g. deleted on another device): the list just catches up.
      if (e instanceof ApiError && e.status === 404) {
        setRows((list) => list?.filter((r) => r.id !== row.id) ?? null);
      } else {
        const message = e instanceof ApiError ? e.message : 'Alıcı silinemedi.';
        setError(message);
        AccessibilityInfo.announceForAccessibility(message);
      }
    } finally {
      setDeleting(null);
    }
  }

  return (
    <Screen>
      <ScreenHeader fallback="/gonder" />
      <View style={styles.copy}>
        <ThemedText type="title">Kayıtlı alıcılar</ThemedText>
        <ThemedText themeColor="textSecondary">
          Yeni bir alıcıyı, ona para gönderdikten sonra transfer özetinden kaydedebilirsiniz.
        </ThemedText>
      </View>

      {error ? (
        <Notice tone="error">
          <ThemedText type="small">{error}</ThemedText>
        </Notice>
      ) : null}

      {rows === null ? (
        <ActivityIndicator color={theme.primary} accessibilityLabel="Alıcılar yükleniyor" />
      ) : rows.length === 0 ? (
        <ThemedText themeColor="textSecondary">Henüz kayıtlı alıcınız yok.</ThemedText>
      ) : (
        <View style={styles.list}>
          {rows.map((row) => (
            <View key={row.id} style={[styles.card, { backgroundColor: theme.backgroundElement }]}>
              <ThemedText type="smallBold">{row.nickname}</ThemedText>
              <ThemedText type="small" themeColor="textSecondary" selectable>
                {row.maskedName} ·{' '}
                {row.iban !== null ? formatIban(row.iban) : `Müşteri no ${row.customerNo}`}
              </ThemedText>
              <Button
                title="Sil"
                variant="secondary"
                accessibilityLabel={`${row.nickname} alıcısını sil`}
                loading={deleting === row.id}
                disabled={deleting !== null}
                onPress={() => remove(row)}
                style={styles.delete}
              />
            </View>
          ))}
        </View>
      )}
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
  list: {
    gap: Spacing.three,
  },
  card: {
    borderRadius: Radius.card,
    padding: Spacing.three,
    gap: Spacing.one,
  },
  delete: {
    marginTop: Spacing.two,
  },
});
