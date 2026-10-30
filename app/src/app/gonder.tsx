import * as Crypto from 'expo-crypto';
import { Redirect, router, useLocalSearchParams } from 'expo-router';
import { useRef, useState } from 'react';
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
import { ApiError, createTransfer, lookupRecipient } from '@/lib/api';
import { formatIban, isValidTrIban, normalizeIban } from '@/lib/banking';
import type { TransferResult } from '@/lib/models';
import { formatKurus, parseTryAmount } from '@/lib/money';
import { refreshCustomer, signOut, useSession } from '@/lib/session';

// Mirrors the API's per-transfer cap (backend/app/config.py: transfer_max_kurus).
const MAX_TRANSFER_KURUS = 5_000_000;

type Recipient =
  | { status: 'idle' }
  | { status: 'checking' }
  | { status: 'found'; maskedName: string }
  | { status: 'error'; message: string };

type Errors = { iban?: string; amount?: string; description?: string; from?: string };

export default function TransferScreen() {
  const theme = useTheme();
  const session = useSession();
  const { hesap } = useLocalSearchParams<{ hesap?: string }>();

  const [step, setStep] = useState<'form' | 'confirm' | 'done'>('form');
  const [fromId, setFromId] = useState<number | null>(hesap ? Number(hesap) : null);
  const [ibanInput, setIbanInput] = useState('TR');
  const [recipient, setRecipient] = useState<Recipient>({ status: 'idle' });
  const [amountInput, setAmountInput] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [sendError, setSendError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<TransferResult | null>(null);

  // One key per confirmed transfer: a retry after a dropped connection reuses it, so the API
  // returns the original transfer instead of sending the money twice.
  const idempotencyKey = useRef<string | null>(null);
  // What the current key was issued for: confirming the same transfer again reuses the key.
  const keyFor = useRef<string | null>(null);
  // Ignores lookup answers for an IBAN the user has since changed.
  const latestLookup = useRef('');

  if (session.status === 'unknown') {
    return (
      <ThemedView style={styles.loading}>
        <ActivityIndicator color={theme.primary} accessibilityLabel="Yükleniyor" />
      </ThemedView>
    );
  }
  if (session.status === 'signedOut') return <Redirect href="/giris" />;

  const accounts = session.customer.accounts;
  const from = accounts.find((a) => a.id === fromId) ?? accounts[0];
  const iban = normalizeIban(ibanInput);
  const amountKurus = parseTryAmount(amountInput);
  // Sending to one of the customer's own accounts: no cap, and the API names the account.
  const ownTarget = accounts.some((a) => a.iban === iban);

  async function onIbanChange(text: string) {
    const cleaned = normalizeIban(text).replace(/[^A-Z0-9]/g, '').slice(0, 26);
    setIbanInput(formatIban(cleaned));
    setErrors((e) => ({ ...e, iban: undefined }));
    latestLookup.current = cleaned;

    if (cleaned.length < 26) {
      setRecipient({ status: 'idle' });
      return;
    }
    if (!isValidTrIban(cleaned)) {
      setRecipient({ status: 'error', message: 'IBAN hatalı görünüyor. Lütfen kontrol edin.' });
      return;
    }
    setRecipient({ status: 'checking' });
    try {
      const found = await lookupRecipient(cleaned);
      if (latestLookup.current === cleaned) {
        setRecipient({ status: 'found', maskedName: found.maskedName });
        AccessibilityInfo.announceForAccessibility(`Alıcı: ${found.maskedName}`);
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return void signOut();
      if (latestLookup.current === cleaned) {
        setRecipient({
          status: 'error',
          message: e instanceof ApiError ? e.message : 'Alıcı bilgisi alınamadı.',
        });
      }
    }
  }

  function goToConfirm() {
    const next: Errors = {};
    if (!from) next.from = 'Gönderen hesabı seçin.';
    if (!isValidTrIban(iban)) next.iban = 'Geçerli bir TR IBAN girin.';
    else if (recipient.status === 'error') next.iban = recipient.message;
    else if (recipient.status !== 'found') next.iban = 'Alıcı bilgisi doğrulanıyor, lütfen bekleyin.';
    else if (from && iban === from.iban) next.iban = 'Aynı hesaba para gönderilemez.';

    if (!amountInput.trim()) next.amount = 'Tutarı girin.';
    else if (amountKurus === null) next.amount = 'Tutarı 1.250,50 biçiminde girin.';
    else if (amountKurus > MAX_TRANSFER_KURUS && !ownTarget)
      next.amount = `Tek seferde en fazla ${formatKurus(MAX_TRANSFER_KURUS)} gönderebilirsiniz.`;
    else if (from && amountKurus > from.balanceKurus)
      next.amount = `Yetersiz bakiye. Kullanılabilir: ${formatKurus(from.balanceKurus)}.`;

    if (description.length > 140) next.description = 'Açıklama en fazla 140 karakter olabilir.';

    setErrors(next);
    const first = Object.values(next)[0];
    if (first) {
      AccessibilityInfo.announceForAccessibility(first);
      return;
    }
    // After an unclear failure the first attempt may have gone through; "Düzenle" without
    // changes must not turn the retry into a second payment.
    const contents = JSON.stringify([from?.id, iban, amountKurus, description.trim()]);
    if (!idempotencyKey.current || keyFor.current !== contents) {
      idempotencyKey.current = Crypto.randomUUID();
      keyFor.current = contents;
    }
    setSendError(null);
    setStep('confirm');
    AccessibilityInfo.announceForAccessibility('Transfer özeti. Bilgileri kontrol edip onaylayın.');
  }

  async function send() {
    if (sending || !from || amountKurus === null || !idempotencyKey.current) return;
    setSending(true);
    setSendError(null);
    try {
      const done = await createTransfer({
        fromAccountId: from.id,
        toIban: iban,
        amountKurus,
        description: description.trim(),
        idempotencyKey: idempotencyKey.current,
      });
      setResult(done);
      setStep('done');
      AccessibilityInfo.announceForAccessibility(
        `${formatKurus(done.amountKurus)} gönderildi.`,
      );
      refreshCustomer().catch(() => {});
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return void signOut();
      const message =
        e instanceof ApiError && e.status === 0
          ? 'Bağlantı kesildi. İşlem tamamlanmış olabilir; "Tekrar dene" aynı işlemi güvenle yeniden gönderir, para iki kez çekilmez.'
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
          {/* Not coral: it fails text contrast on white (MARKA.md §5). */}
          <ThemedText type="label" themeColor="textSecondary">
            Transfer tamamlandı
          </ThemedText>
          <ThemedText type="title">{formatKurus(result.amountKurus)}</ThemedText>
          <ThemedText themeColor="textSecondary">
            {ownTarget
              ? `${result.recipient} hesabınıza gönderildi.`
              : `${result.recipient} adlı alıcıya gönderildi.`}
          </ThemedText>
        </View>
        <Summary
          rows={[
            ['Alıcı IBAN', formatIban(result.toIban)],
            ['Açıklama', result.description],
            ['Hesabınızdaki yeni bakiye', formatKurus(result.fromBalanceAfterKurus)],
          ]}
        />
        <View style={styles.actions}>
          <Button title="Hesabıma dön" onPress={() => router.replace('/hesabim')} />
          <Button
            title="Yeni transfer"
            variant="secondary"
            onPress={() => {
              // A new transfer, even with identical details, must not replay the finished one.
              idempotencyKey.current = null;
              setStep('form');
              setResult(null);
              setIbanInput('TR');
              setRecipient({ status: 'idle' });
              setAmountInput('');
              setDescription('');
            }}
          />
        </View>
      </Screen>
    );
  }

  if (step === 'confirm' && from && amountKurus !== null && recipient.status === 'found') {
    return (
      <Screen>
        <ScreenHeader fallback="/hesabim" />
        <View style={styles.copy}>
          <ThemedText type="title">Onaylıyor musunuz?</ThemedText>
          <ThemedText themeColor="textSecondary">Gönderilen para geri alınamaz.</ThemedText>
        </View>
        <Summary
          rows={[
            ['Tutar', formatKurus(amountKurus)],
            ['Alıcı', recipient.maskedName],
            ['Alıcı IBAN', formatIban(iban)],
            ['Gönderen hesap', `${from.name} · ${formatKurus(from.balanceKurus)}`],
            [
              'Açıklama',
              description.trim() || (ownTarget ? 'Hesaplar arası transfer' : 'Para transferi'),
            ],
          ]}
        />
        {sendError ? (
          <Notice tone="error">
            <ThemedText type="small">{sendError}</ThemedText>
          </Notice>
        ) : null}
        <View style={styles.actions}>
          <Button
            title={sendError ? 'Tekrar dene' : 'Onayla ve gönder'}
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
        <ThemedText type="title">Para gönder</ThemedText>
        <ThemedText themeColor="textSecondary">
          Şimdilik yalnızca AB Bank hesaplarına gönderim yapılabilir.
        </ThemedText>
      </View>

      <View style={styles.form}>
        <ChoiceList
          label="Gönderen hesap"
          value={from?.id ?? null}
          onChange={setFromId}
          choices={accounts.map((a) => ({
            value: a.id,
            title: a.name,
            detail: formatKurus(a.balanceKurus),
          }))}
        />
        {errors.from ? (
          <ThemedText type="small" themeColor="danger">
            {errors.from}
          </ThemedText>
        ) : null}

        <View style={styles.field}>
          <TextField
            label="Alıcı IBAN"
            value={ibanInput}
            onChangeText={onIbanChange}
            autoCapitalize="characters"
            autoCorrect={false}
            autoComplete="off"
            error={errors.iban ?? (recipient.status === 'error' ? recipient.message : undefined)}
          />
          {recipient.status === 'checking' ? (
            <ThemedText type="small" themeColor="textSecondary">
              Alıcı doğrulanıyor…
            </ThemedText>
          ) : recipient.status === 'found' ? (
            <ThemedText type="small" accessibilityLiveRegion="polite">
              Alıcı: <ThemedText type="smallBold">{recipient.maskedName}</ThemedText>
            </ThemedText>
          ) : null}
        </View>

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

      <Button title="Devam" onPress={goToConfirm} disabled={recipient.status === 'checking'} />
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
  field: {
    gap: Spacing.one,
  },
  actions: {
    gap: Spacing.three,
  },
});
