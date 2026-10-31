import { Redirect, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, ActivityIndicator, RefreshControl, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Button } from '@/components/ui/button';
import { Notice } from '@/components/ui/notice';
import { Screen } from '@/components/ui/screen';
import { ScreenHeader } from '@/components/ui/screen-header';
import { TextField } from '@/components/ui/text-field';
import { Radius, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { isValidReason, MAX_REASON_LENGTH, type AdminCustomerDetail } from '@/lib/admin';
import {
  adminFetchCustomer,
  adminFetchMovements,
  adminSetFrozen,
  adminUnlockCustomer,
  ApiError,
} from '@/lib/api';
import { formatIban } from '@/lib/banking';
import { debtKurus, type Account, type Movement } from '@/lib/models';
import { formatKurus } from '@/lib/money';
import { signOut, useSession } from '@/lib/session';

const dateFormatter = new Intl.DateTimeFormat('tr-TR', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

const KIND_LABELS: Record<Account['kind'], string> = {
  checking: 'Vadesiz',
  savings: 'Birikim',
  credit: 'Kredili',
};

/** One customer as an admin sees them: accounts, recent movements, and the actions allowed. */
export default function AdminCustomerScreen() {
  const theme = useTheme();
  const session = useSession();
  const { id } = useLocalSearchParams<{ id: string }>();
  const customerId = Number(id);

  const [customer, setCustomer] = useState<AdminCustomerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [reason, setReason] = useState('');
  // Which action is running: 'unlock', or the id of the account being (un)frozen.
  const [busy, setBusy] = useState<'unlock' | number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  // Bumped by every load and every change: only the newest answer may replace what is shown, so
  // a refresh that started before a freeze can't bring back the unfrozen account.
  const version = useRef(0);
  // Bumped by pull-to-refresh: account cards start over and reload their movements.
  const [reloads, setReloads] = useState(0);

  const handleError = useCallback((e: unknown, fallback: string) => {
    if (e instanceof ApiError && e.status === 401) return void signOut();
    const message = e instanceof ApiError ? e.message : fallback;
    setError(message);
    AccessibilityInfo.announceForAccessibility(message);
  }, []);

  const load = useCallback(async () => {
    const started = ++version.current;
    try {
      const fresh = await adminFetchCustomer(customerId);
      if (started === version.current) setCustomer(fresh);
    } catch (e) {
      if (started === version.current) handleError(e, 'Müşteri bilgileri yüklenemedi.');
    }
  }, [customerId, handleError]);

  const isAdmin = session.status === 'signedIn' && session.customer.isAdmin;
  useEffect(() => {
    if (!isAdmin) return;
    let cancelled = false;
    const started = ++version.current;
    adminFetchCustomer(customerId)
      .then(
        (c) => {
          if (!cancelled && started === version.current) setCustomer(c);
        },
        (e) => {
          if (!cancelled) handleError(e, 'Müşteri bilgileri yüklenemedi.');
        },
      )
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isAdmin, customerId, handleError]);

  if (session.status === 'unknown') {
    return (
      <ThemedView style={styles.loading}>
        <ActivityIndicator color={theme.primary} accessibilityLabel="Yükleniyor" />
      </ThemedView>
    );
  }
  if (session.status === 'signedOut') return <Redirect href="/giris" />;
  if (!session.customer.isAdmin) return <Redirect href="/hesabim" />;

  // The API refuses an admin's actions on their own record; don't offer them.
  const self = customer?.customerNo === session.customer.customerNo;
  const reasonOk = isValidReason(reason);

  async function onRefresh() {
    setRefreshing(true);
    setError(null);
    setReloads((n) => n + 1);
    await load();
    setRefreshing(false);
  }

  async function run(action: 'unlock' | number, task: () => Promise<string>) {
    if (busy !== null || !reasonOk) return;
    setBusy(action);
    setError(null);
    setDone(null);
    try {
      const message = await task();
      setReason('');
      setDone(message);
      AccessibilityInfo.announceForAccessibility(message);
    } catch (e) {
      handleError(e, 'İşlem yapılamadı. Lütfen tekrar deneyin.');
      // E.g. another admin changed it first (409): show what is true now.
      await load();
    } finally {
      setBusy(null);
    }
  }

  function toggleFrozen(account: Account) {
    const freeze = !account.frozen;
    run(account.id, async () => {
      const updated = await adminSetFrozen(account.id, freeze, reason.trim());
      version.current++;
      setCustomer((c) =>
        c && { ...c, accounts: c.accounts.map((a) => (a.id === updated.id ? updated : a)) },
      );
      return freeze ? `${account.name} donduruldu.` : `${account.name} için dondurma kaldırıldı.`;
    });
  }

  function unlock() {
    if (!customer) return;
    run('unlock', async () => {
      const updated = await adminUnlockCustomer(customer.id, reason.trim());
      version.current++;
      setCustomer((c) => c && { ...c, ...updated });
      return 'Giriş kilidi açıldı.';
    });
  }

  return (
    <Screen
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} />
      }>
      <ScreenHeader fallback="/yonetici" />

      {loading ? (
        <ActivityIndicator color={theme.primary} accessibilityLabel="Müşteri yükleniyor" />
      ) : null}

      {customer ? (
        <View style={styles.copy}>
          <ThemedText type="title">{customer.fullName}</ThemedText>
          <ThemedText themeColor="textSecondary" selectable>
            Müşteri no {customer.customerNo}
            {customer.isAdmin ? ' · Yönetici' : ''}
          </ThemedText>
          <ThemedText type="small" themeColor="textSecondary">
            Kayıt: {dateFormatter.format(new Date(customer.createdAt))}
          </ThemedText>
        </View>
      ) : null}

      {error ? (
        <Notice tone="error">
          <ThemedText type="small">{error}</ThemedText>
        </Notice>
      ) : null}
      {done ? (
        <Notice tone="info">
          <ThemedText type="small">{done}</ThemedText>
        </Notice>
      ) : null}

      {customer && self ? (
        <Notice tone="info">
          <ThemedText type="small">
            Bu sizin kaydınız. Kendi hesaplarınızda işlemi başka bir yönetici yapmalıdır.
          </ThemedText>
        </Notice>
      ) : null}

      {customer && !self ? (
        <View style={styles.section}>
          <TextField
            label="Gerekçe (işlem kaydına yazılır)"
            placeholder="Örn. müşteri telefonla kartının çalındığını bildirdi"
            value={reason}
            onChangeText={(v) => {
              setReason(v);
              setDone(null);
            }}
            maxLength={MAX_REASON_LENGTH}
          />
          {customer.locked ? (
            <View style={styles.section}>
              <ThemedText type="small" themeColor="danger">
                Hatalı şifre denemeleri yüzünden müşterinin girişi geçici olarak kilitli.
              </ThemedText>
              <Button
                title="Giriş kilidini aç"
                loading={busy === 'unlock'}
                disabled={!reasonOk || busy !== null}
                onPress={unlock}
              />
            </View>
          ) : null}
          {!reasonOk ? (
            <ThemedText type="small" themeColor="textSecondary">
              İşlem yapmak için önce bir gerekçe yazın.
            </ThemedText>
          ) : null}
        </View>
      ) : null}

      {customer ? (
        <View style={styles.section}>
          <ThemedText type="subtitle">Hesaplar</ThemedText>
          {customer.accounts.length === 0 ? (
            <ThemedText themeColor="textSecondary">Müşterinin hesabı yok.</ThemedText>
          ) : null}
          {customer.accounts.map((account) => (
            <AccountCard
              key={`${account.id}-${reloads}`}
              account={account}
              actions={!self}
              busy={busy === account.id}
              disabled={!reasonOk || busy !== null}
              onToggleFrozen={() => toggleFrozen(account)}
            />
          ))}
        </View>
      ) : null}
    </Screen>
  );
}

type AccountCardProps = {
  account: Account;
  actions: boolean;
  busy: boolean;
  disabled: boolean;
  onToggleFrozen: () => void;
};

function AccountCard({ account, actions, busy, disabled, onToggleFrozen }: AccountCardProps) {
  const theme = useTheme();
  const [movements, setMovements] = useState<Movement[] | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const amount =
    account.kind === 'credit'
      ? `Borç ${formatKurus(debtKurus(account))} / limit ${formatKurus(account.creditLimitKurus ?? 0)}`
      : formatKurus(account.balanceKurus);

  async function toggleMovements() {
    if (open) return setOpen(false);
    setOpen(true);
    if (movements !== null) return;
    setLoading(true);
    setError(null);
    try {
      setMovements((await adminFetchMovements(account.id, null, 10)).items);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return void signOut();
      setError(e instanceof ApiError ? e.message : 'Hareketler yüklenemedi.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={[styles.card, { backgroundColor: theme.backgroundElement }]}>
      <ThemedText type="label" themeColor="textSecondary">
        {account.name} · {KIND_LABELS[account.kind]} · #{account.id}
      </ThemedText>
      <ThemedText type="subtitle">{amount}</ThemedText>
      <ThemedText type="small" themeColor="textSecondary" selectable>
        {formatIban(account.iban)}
      </ThemedText>
      {account.frozen ? (
        <ThemedText type="smallBold" themeColor="danger">
          Dondurulmuş · para çıkışı kapalı
        </ThemedText>
      ) : null}

      <View style={styles.cardActions}>
        {actions ? (
          <Button
            title={account.frozen ? 'Dondurmayı kaldır' : 'Hesabı dondur'}
            variant={account.frozen ? 'secondary' : 'primary'}
            loading={busy}
            disabled={disabled}
            onPress={onToggleFrozen}
          />
        ) : null}
        <Button
          title={open ? 'Hareketleri gizle' : 'Son hareketler'}
          variant="secondary"
          onPress={toggleMovements}
        />
      </View>

      {open ? (
        <View style={styles.movements}>
          {loading ? (
            <ActivityIndicator color={theme.primary} accessibilityLabel="Hareketler yükleniyor" />
          ) : null}
          {error ? (
            <ThemedText type="small" themeColor="danger">
              {error}
            </ThemedText>
          ) : null}
          {movements?.length === 0 ? (
            <ThemedText type="small" themeColor="textSecondary">
              Bu hesapta hareket yok.
            </ThemedText>
          ) : null}
          {movements?.map((m) => <MovementRow key={m.id} movement={m} />)}
        </View>
      ) : null}
    </View>
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
    gap: Spacing.one,
  },
  section: {
    gap: Spacing.three,
  },
  card: {
    borderRadius: Radius.card,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  cardActions: {
    gap: Spacing.two,
    marginTop: Spacing.two,
  },
  movements: {
    gap: Spacing.two,
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
