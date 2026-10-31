import { Redirect, useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, ActivityIndicator, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Button } from '@/components/ui/button';
import { ChoiceList } from '@/components/ui/choice-list';
import { Notice } from '@/components/ui/notice';
import { Screen } from '@/components/ui/screen';
import { ScreenHeader } from '@/components/ui/screen-header';
import { TextField } from '@/components/ui/text-field';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { ApiError, fetchMovements, fetchStatementCsv } from '@/lib/api';
import type { Movement } from '@/lib/models';
import { formatKurus } from '@/lib/money';
import { signOut, useSession } from '@/lib/session';
import {
  formatIsoDate,
  presetRange,
  rangeError,
  statementFilename,
  type DateRange,
  type RangePreset,
  turkishDateFormatter,
} from '@/lib/statement';
import { deliverStatement } from '@/lib/statement-file';
import { formatDateInput, parseTrDate } from '@/lib/validation';

type Choice = RangePreset | 'custom';

const CHOICES: { value: Choice; title: string }[] = [
  { value: 'thisMonth', title: 'Bu ay' },
  { value: 'last30', title: 'Son 30 gün' },
  { value: 'last90', title: 'Son 3 ay' },
  { value: 'custom', title: 'Tarih aralığı seç' },
];

const dateFormatter = turkishDateFormatter({
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
});

/** Movements of one account in a date range, and that range as a CSV statement. */
export default function StatementScreen() {
  const theme = useTheme();
  const session = useSession();
  const { id } = useLocalSearchParams<{ id: string }>();
  const accountId = Number(id);

  const [choice, setChoice] = useState<Choice>('thisMonth');
  const [fromInput, setFromInput] = useState('');
  const [toInput, setToInput] = useState('');
  const [items, setItems] = useState<Movement[]>([]);
  const [nextBeforeId, setNextBeforeId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  // Bumped by every range change, so the list reloads even when two choices give the same dates.
  const [reload, setReload] = useState(0);
  const [listError, setListError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  // Bumped whenever the range changes: pages for an older range are dropped.
  const request = useRef(0);

  // The range the screen shows; null while a custom range is incomplete or invalid.
  let range: DateRange | null = null;
  let customError: string | null = null;
  if (choice !== 'custom') range = presetRange(choice);
  else {
    const from = parseTrDate(fromInput);
    const to = parseTrDate(toInput);
    if (from && to) {
      customError = rangeError({ from, to });
      if (!customError) range = { from, to };
    } else if (fromInput.length === 10 || toInput.length === 10) {
      if ((fromInput.length === 10 && !from) || (toInput.length === 10 && !to))
        customError = 'Tarihi GG.AA.YYYY biçiminde girin.';
    }
  }
  const rangeKey = range ? `${range.from}/${range.to}` : null;

  const signedIn = session.status === 'signedIn';
  useEffect(() => {
    if (!signedIn || !rangeKey) return;
    const [from, to] = rangeKey.split('/');
    const started = ++request.current;
    fetchMovements(accountId, null, 20, { from, to }).then(
      (page) => {
        if (started !== request.current) return;
        setItems(page.items);
        setNextBeforeId(page.nextBeforeId);
        setListError(null);
        setLoading(false);
      },
      (e) => {
        if (started !== request.current) return;
        if (e instanceof ApiError && e.status === 401) return void signOut();
        setItems([]);
        setNextBeforeId(null);
        setListError(e instanceof ApiError ? e.message : 'Hareketler yüklenemedi.');
        setLoading(false);
      },
    );
  }, [signedIn, accountId, rangeKey, reload]);

  if (session.status === 'unknown') {
    return (
      <ThemedView style={styles.loading}>
        <ActivityIndicator color={theme.primary} accessibilityLabel="Yükleniyor" />
      </ThemedView>
    );
  }
  if (session.status === 'signedOut') return <Redirect href="/giris" />;
  const account = session.customer.accounts.find((a) => a.id === accountId);
  if (!account) return <Redirect href="/hesabim" />;

  function changeRange(update: () => void) {
    // A new range starts loading at once, so the old list isn't shown as if it were the new one.
    request.current++;
    update();
    setItems([]);
    setNextBeforeId(null);
    setListError(null);
    setExportError(null);
    setLoading(true);
    setReload((n) => n + 1);
  }

  async function loadMore() {
    if (!range || nextBeforeId === null || loading) return;
    const started = request.current;
    setLoading(true);
    try {
      const page = await fetchMovements(accountId, nextBeforeId, 20, range);
      if (started !== request.current) return;
      setItems((prev) => [...prev, ...page.items]);
      setNextBeforeId(page.nextBeforeId);
    } catch (e) {
      if (started !== request.current) return;
      if (e instanceof ApiError && e.status === 401) return void signOut();
      setListError(e instanceof ApiError ? e.message : 'Hareketler yüklenemedi.');
    } finally {
      if (started === request.current) setLoading(false);
    }
  }

  async function exportCsv() {
    if (!range || !account || exporting) return;
    // A failure for a range the user has since left must not show under the new one.
    const started = request.current;
    setExporting(true);
    setExportError(null);
    try {
      const csv = await fetchStatementCsv(account.id, range);
      await deliverStatement(statementFilename(account.iban, range), csv);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return void signOut();
      if (started !== request.current) return;
      const message =
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : 'Ekstre oluşturulamadı.';
      setExportError(message);
      AccessibilityInfo.announceForAccessibility(message);
    } finally {
      setExporting(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader fallback="/hesabim" />
      <View style={styles.copy}>
        <ThemedText themeColor="textSecondary">{account.name}</ThemedText>
        <ThemedText type="title">Hesap özeti</ThemedText>
        <ThemedText themeColor="textSecondary">
          Bir tarih aralığı seçin; hareketleri görün veya CSV dosyası olarak indirin. Dosya Excel&apos;de
          açılabilir.
        </ThemedText>
      </View>

      <ChoiceList
        label="Aralık"
        value={choice}
        onChange={(next) => changeRange(() => setChoice(next))}
        choices={CHOICES}
      />

      {choice === 'custom' ? (
        <View style={styles.dates}>
          <View style={styles.date}>
            <TextField
              label="Başlangıç"
              placeholder="GG.AA.YYYY"
              value={fromInput}
              onChangeText={(v) => changeRange(() => setFromInput(formatDateInput(v)))}
              keyboardType="number-pad"
              maxLength={10}
            />
          </View>
          <View style={styles.date}>
            <TextField
              label="Bitiş"
              placeholder="GG.AA.YYYY"
              value={toInput}
              onChangeText={(v) => changeRange(() => setToInput(formatDateInput(v)))}
              keyboardType="number-pad"
              maxLength={10}
            />
          </View>
        </View>
      ) : null}
      {customError ? (
        <ThemedText type="small" themeColor="danger" accessibilityLiveRegion="polite">
          {customError}
        </ThemedText>
      ) : null}

      {range ? (
        <View style={styles.section}>
          <ThemedText type="small" themeColor="textSecondary">
            {formatIsoDate(range.from)} – {formatIsoDate(range.to)}
          </ThemedText>
          <Button
            title="CSV olarak indir"
            onPress={exportCsv}
            loading={exporting}
            accessibilityLabel={`${formatIsoDate(range.from)} ile ${formatIsoDate(range.to)} arası ekstreyi CSV olarak indir`}
          />
          {exportError ? (
            <Notice tone="error">
              <ThemedText type="small">{exportError}</ThemedText>
            </Notice>
          ) : null}
        </View>
      ) : null}

      {range ? (
        <View style={styles.section}>
          <ThemedText type="subtitle">Hareketler</ThemedText>
          {listError ? (
            <Notice tone="error">
              <ThemedText type="small">{listError}</ThemedText>
            </Notice>
          ) : null}
          {items.map((m) => (
            <MovementRow key={m.id} movement={m} />
          ))}
          {loading ? (
            <ActivityIndicator color={theme.primary} accessibilityLabel="Hareketler yükleniyor" />
          ) : items.length === 0 && !listError ? (
            <ThemedText themeColor="textSecondary">Bu aralıkta hareket yok.</ThemedText>
          ) : null}
          {nextBeforeId !== null && !loading ? (
            <Button title="Daha fazla göster" variant="secondary" onPress={loadMore} />
          ) : null}
        </View>
      ) : null}
    </Screen>
  );
}

function MovementRow({ movement }: { movement: Movement }) {
  const incoming = movement.amountKurus > 0;
  const amount = `${incoming ? '+' : '−'}${formatKurus(Math.abs(movement.amountKurus))}`;
  const title = movement.counterparty
    ? `${movement.description} · ${movement.counterparty}`
    : movement.description;
  const when = dateFormatter.format(new Date(movement.createdAt));
  return (
    <View
      style={styles.row}
      accessible
      accessibilityLabel={`${title}, ${incoming ? 'gelen' : 'giden'} ${formatKurus(
        Math.abs(movement.amountKurus),
      )}, ${when}`}>
      <View style={styles.rowText}>
        <ThemedText type="smallBold" numberOfLines={1}>
          {title}
        </ThemedText>
        <ThemedText type="small" themeColor="textSecondary">
          {when}
        </ThemedText>
      </View>
      <ThemedText type="smallBold">{amount}</ThemedText>
    </View>
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
  dates: {
    flexDirection: 'row',
    gap: Spacing.three,
  },
  date: {
    flex: 1,
  },
  section: {
    gap: Spacing.three,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
  },
  rowText: {
    flex: 1,
    gap: Spacing.half,
  },
});
