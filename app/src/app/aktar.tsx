import * as Crypto from 'expo-crypto';
import { Redirect, router, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, ActivityIndicator, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Button } from '@/components/ui/button';
import { ChoiceList } from '@/components/ui/choice-list';
import { Notice } from '@/components/ui/notice';
import { Screen } from '@/components/ui/screen';
import { ScreenHeader } from '@/components/ui/screen-header';
import { Summary } from '@/components/ui/summary';
import { TextField } from '@/components/ui/text-field';
import { Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { ApiError, createTransfer } from '@/lib/api';
import { availableKurus, debtKurus, type Account, type TransferResult } from '@/lib/models';
import { formatKurus, parseTryAmount } from '@/lib/money';
import { refreshCustomer, signOut, useSession } from '@/lib/session';

type Errors = { amount?: string; description?: string };

/** Moves money between the customer's own accounts; no IBAN, no recipient check, no limits. */
export default function OwnTransferScreen() {
  const theme = useTheme();
  const session = useSession();
  const { hesap } = useLocalSearchParams<{ hesap?: string }>();

  const [step, setStep] = useState<'form' | 'confirm' | 'done'>('form');
  const [fromId, setFromId] = useState<number | null>(hesap ? Number(hesap) : null);
  const [toId, setToId] = useState<number | null>(null);
  const [amountInput, setAmountInput] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [sendError, setSendError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<TransferResult | null>(null);
  // Set when reloading balances after a transfer failed: the shown balances may be out of date,
  // so the client stops blocking on them and leaves the balance check to the API.
  const [balancesStale, setBalancesStale] = useState(false);

  // Only the latest reload decides the flag: an older one finishing last says nothing about
  // the balances now in the session.
  const reloads = useRef(0);
  // While a reload runs the session may still hold pre-transfer balances, so don't block on them.
  // Starts true for the reload on mount; callers set it before any later reload.
  const [reloading, setReloading] = useState(true);
  const reloadBalances = useCallback(() => {
    const reload = ++reloads.current;
    const settle = (stale: boolean) => {
      if (reload !== reloads.current) return;
      setBalancesStale(stale);
      setReloading(false);
    };
    refreshCustomer().then(
      () => settle(false),
      () => settle(true),
    );
  }, []);

  // Balances in the session may predate a transfer whose reload failed; fetch fresh ones.
  const signedIn = session.status === 'signedIn';
  useEffect(() => {
    if (signedIn) reloadBalances();
  }, [signedIn, reloadBalances]);

  // Same retry rules as gonder.tsx: one key per transfer contents, reused after an unclear failure.
  const idempotencyKey = useRef<string | null>(null);
  const keyFor = useRef<string | null>(null);

  if (session.status === 'unknown') {
    return (
      <ThemedView style={styles.loading}>
        <ActivityIndicator color={theme.primary} accessibilityLabel="Yükleniyor" />
      </ThemedView>
    );
  }
  if (session.status === 'signedOut') return <Redirect href="/giris" />;

  const accounts = session.customer.accounts;
  // Nothing leaves a frozen account, but it can still receive.
  const sources = accounts.filter((a) => !a.frozen);
  const from = sources.find((a) => a.id === fromId) ?? sources[0];
  // The target can never be the source: picking the target's account as source moves it on.
  const targets = accounts.filter((a) => a.id !== from?.id);
  const to = targets.find((a) => a.id === toId) ?? targets[0];
  const amountKurus = parseTryAmount(amountInput);

  if (!from || !to) {
    return (
      <Screen>
        <ScreenHeader fallback="/hesabim" />
        <View style={styles.copy}>
          <ThemedText type="title">Hesaplarım arası</ThemedText>
          <ThemedText themeColor="textSecondary">
            {accounts.length >= 2
              ? 'Hesaplarınız dondurulmuş; şu anda hiçbirinden para aktarılamaz.'
              : 'Hesaplarınız arasında para aktarmak için en az iki hesabınız olmalı.'}
          </ThemedText>
        </View>
        {accounts.length < 2 ? (
          <Button title="Yeni hesap aç" onPress={() => router.replace('/hesap-ac')} />
        ) : null}
      </Screen>
    );
  }

  function goToConfirm() {
    if (!from || !to) return;
    const next: Errors = {};
    if (!amountInput.trim()) next.amount = 'Tutarı girin.';
    else if (amountKurus === null) next.amount = 'Tutarı 1.250,50 biçiminde girin.';
    else if (!balancesStale && !reloading && amountKurus > availableKurus(from))
      next.amount =
        from.kind === 'credit'
          ? `Kullanılabilir limit yetersiz. Kullanılabilir: ${formatKurus(availableKurus(from))}.`
          : `Yetersiz bakiye. Kullanılabilir: ${formatKurus(from.balanceKurus)}.`;
    else if (!balancesStale && !reloading && to.kind === 'credit' && amountKurus > debtKurus(to))
      next.amount =
        debtKurus(to) === 0
          ? 'Bu kredili hesapta borcunuz yok.'
          : `Ödeme borcunuzdan fazla olamaz. Borç: ${formatKurus(debtKurus(to))}.`;
    if (description.length > 140) next.description = 'Açıklama en fazla 140 karakter olabilir.';

    setErrors(next);
    const first = Object.values(next)[0];
    if (first) {
      AccessibilityInfo.announceForAccessibility(first);
      return;
    }
    const contents = JSON.stringify([from.id, to.iban, amountKurus, description.trim()]);
    if (!idempotencyKey.current || keyFor.current !== contents) {
      idempotencyKey.current = Crypto.randomUUID();
      keyFor.current = contents;
    }
    setSendError(null);
    setStep('confirm');
    AccessibilityInfo.announceForAccessibility('Aktarım özeti. Bilgileri kontrol edip onaylayın.');
  }

  async function send() {
    if (sending || !from || !to || amountKurus === null || !idempotencyKey.current) return;
    setSending(true);
    setSendError(null);
    try {
      const done = await createTransfer({
        fromAccountId: from.id,
        toIban: to.iban,
        amountKurus,
        description: description.trim(),
        idempotencyKey: idempotencyKey.current,
      });
      setResult(done);
      setStep('done');
      AccessibilityInfo.announceForAccessibility(`${formatKurus(done.amountKurus)} aktarıldı.`);
      setReloading(true);
      reloadBalances();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return void signOut();
      const message =
        e instanceof ApiError && e.status === 0
          ? 'Bağlantı kesildi. İşlem tamamlanmış olabilir; "Tekrar dene" aynı işlemi güvenle yeniden gönderir, para iki kez aktarılmaz.'
          : e instanceof ApiError
            ? e.message
            : 'Beklenmeyen bir hata oluştu.';
      setSendError(message);
      AccessibilityInfo.announceForAccessibility(message);
    } finally {
      setSending(false);
    }
  }

  if (step === 'done' && result) {
    return (
      <Screen>
        <View style={styles.copy}>
          <ThemedText type="label" themeColor="textSecondary">
            Aktarım tamamlandı
          </ThemedText>
          <ThemedText type="title">{formatKurus(result.amountKurus)}</ThemedText>
          <ThemedText themeColor="textSecondary">{result.recipient} hesabınıza aktarıldı.</ThemedText>
        </View>
        <Summary
          rows={[
            ['Açıklama', result.description],
            [`${from.name} yeni bakiyesi`, formatKurus(result.fromBalanceAfterKurus)],
          ]}
        />
        <View style={styles.actions}>
          <Button title="Hesabıma dön" onPress={() => router.replace('/hesabim')} />
          <Button
            title="Yeni aktarım"
            variant="secondary"
            onPress={() => {
              idempotencyKey.current = null;
              setStep('form');
              setResult(null);
              setAmountInput('');
              setDescription('');
            }}
          />
        </View>
      </Screen>
    );
  }

  if (step === 'confirm' && amountKurus !== null) {
    return (
      <Screen>
        <ScreenHeader fallback="/hesabim" />
        <View style={styles.copy}>
          <ThemedText type="title">Onaylıyor musunuz?</ThemedText>
        </View>
        <Summary
          rows={[
            ['Tutar', formatKurus(amountKurus)],
            ['Gönderen hesap', `${from.name} · ${accountDetail(from)}`],
            ['Alıcı hesap', `${to.name} · ${accountDetail(to)}`],
            ['Açıklama', description.trim() || 'Hesaplar arası transfer'],
          ]}
        />
        {sendError ? (
          <Notice tone="error">
            <ThemedText type="small">{sendError}</ThemedText>
          </Notice>
        ) : null}
        <View style={styles.actions}>
          <Button
            title={sendError ? 'Tekrar dene' : 'Onayla ve aktar'}
            onPress={send}
            loading={sending}
          />
          <Button
            title="Düzenle"
            variant="secondary"
            disabled={sending}
            onPress={() => setStep('form')}
          />
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader fallback="/hesabim" />
      <View style={styles.copy}>
        <ThemedText type="title">Hesaplarım arası</ThemedText>
        <ThemedText themeColor="textSecondary">
          Kendi hesaplarınız arasındaki aktarımlar transfer limitlerinize sayılmaz.
        </ThemedText>
      </View>

      {balancesStale ? (
        <Notice tone="error">
          <ThemedText type="small">
            Bakiyeler güncellenemedi; gösterilen tutarlar eski olabilir. Bakiye kontrolü gönderimde
            yapılır.
          </ThemedText>
        </Notice>
      ) : null}

      <View style={styles.form}>
        <ChoiceList
          label="Gönderen hesap"
          value={from.id}
          onChange={setFromId}
          choices={sources.map((a) => ({
            value: a.id,
            title: a.name,
            detail: accountDetail(a),
          }))}
        />
        <ChoiceList
          label="Alıcı hesap"
          value={to.id}
          onChange={setToId}
          choices={targets.map((a) => ({
            value: a.id,
            title: a.name,
            detail: accountDetail(a),
          }))}
        />

        <View style={styles.field}>
          <TextField
            label="Tutar (TL)"
            placeholder="0,00"
            value={amountInput}
            onChangeText={(v) => {
              setAmountInput(v.replace(/[^\d.,]/g, '').slice(0, 18));
              setErrors((e) => ({ ...e, amount: undefined }));
            }}
            keyboardType="decimal-pad"
            error={errors.amount}
          />
          {amountKurus !== null && !errors.amount ? (
            <ThemedText type="small" themeColor="textSecondary">
              {formatKurus(amountKurus)}
            </ThemedText>
          ) : null}
        </View>

        <TextField
          label="Açıklama (isteğe bağlı)"
          value={description}
          onChangeText={setDescription}
          maxLength={140}
          returnKeyType="next"
          onSubmitEditing={goToConfirm}
          error={errors.description}
        />
      </View>

      <Button title="Devam" onPress={goToConfirm} />
    </Screen>
  );
}

/** Balance for regular accounts; debt and what's left of the limit for a credit account. */
function accountDetail(account: Account): string {
  if (account.kind !== 'credit') return formatKurus(account.balanceKurus);
  return `Borç ${formatKurus(debtKurus(account))}, kullanılabilir ${formatKurus(availableKurus(account))}`;
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
  field: {
    gap: Spacing.one,
  },
  actions: {
    gap: Spacing.three,
  },
});
