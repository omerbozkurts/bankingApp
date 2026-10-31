import * as Crypto from 'expo-crypto';
import { Redirect, router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { AccessibilityInfo, ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';

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
import {
  ApiError,
  createTransfer,
  fetchSavedRecipients,
  lookupRecipient,
  saveRecipient,
} from '@/lib/api';
import { formatIban, isValidTrIban, normalizeIban } from '@/lib/banking';
import {
  debtKurus,
  paymentAccount,
  sameTarget,
  savedTarget,
  type RecipientTarget,
  type SavedRecipient,
  type TransferResult,
} from '@/lib/models';
import { formatKurus, parseTryAmount } from '@/lib/money';
import { refreshCustomer, signOut, useSession } from '@/lib/session';
import { digitsOnly } from '@/lib/validation';

// Mirrors the API's per-transfer cap (backend/app/config.py: transfer_max_kurus).
const MAX_TRANSFER_KURUS = 5_000_000;

type Recipient =
  | { status: 'idle' }
  | { status: 'checking' }
  // `iban` is masked when the recipient was found by customer number.
  | { status: 'found'; maskedName: string; iban: string }
  | { status: 'error'; message: string };

type Errors = { recipient?: string; amount?: string; description?: string; from?: string };

/** How the recipient is addressed. */
type Mode = 'iban' | 'customerNo';

const MODES: { value: Mode; title: string; detail: string }[] = [
  { value: 'iban', title: 'IBAN ile', detail: 'Herhangi bir AB Bank hesabına' },
  { value: 'customerNo', title: 'Müşteri no ile', detail: 'Alıcının vadesiz hesabına' },
];

export default function TransferScreen() {
  const theme = useTheme();
  const session = useSession();
  const { hesap } = useLocalSearchParams<{ hesap?: string }>();

  const [step, setStep] = useState<'form' | 'confirm' | 'done'>('form');
  const [fromId, setFromId] = useState<number | null>(hesap ? Number(hesap) : null);
  const [mode, setMode] = useState<Mode>('iban');
  const [ibanInput, setIbanInput] = useState('TR');
  const [customerNoInput, setCustomerNoInput] = useState('');
  const [recipient, setRecipient] = useState<Recipient>({ status: 'idle' });
  const [amountInput, setAmountInput] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [sendError, setSendError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<TransferResult | null>(null);
  const [saved, setSaved] = useState<SavedRecipient[]>([]);
  const [saveName, setSaveName] = useState('');
  const [saveState, setSaveState] = useState<
    { status: 'idle' | 'saving' | 'saved' } | { status: 'error'; message: string }
  >({ status: 'idle' });

  // One key per confirmed transfer: a retry after a dropped connection reuses it, so the API
  // returns the original transfer instead of sending the money twice.
  const idempotencyKey = useRef<string | null>(null);
  // What the current key was issued for: confirming the same transfer again reuses the key.
  const keyFor = useRef<string | null>(null);
  // Ignores lookup answers for a recipient the user has since changed.
  const latestLookup = useRef('');

  // Bumped by "Yeni transfer": a save still running for the finished transfer must not mark the
  // next one's recipient as saved.
  const transferRun = useRef(0);
  // Bumped by every list load and every save: a load that started before a save would drop the
  // newly saved row, so only the newest change may replace the list.
  const listVersion = useRef(0);

  // Reloaded whenever the screen comes back into view, e.g. after managing the list.
  const signedIn = session.status === 'signedIn';
  useFocusEffect(
    useCallback(() => {
      if (!signedIn) return;
      let cancelled = false;
      const started = ++listVersion.current;
      // The list is a shortcut: if it can't load, the form still works without it.
      fetchSavedRecipients().then(
        (rows) => {
          if (!cancelled && started === listVersion.current) setSaved(rows);
        },
        () => {},
      );
      return () => {
        cancelled = true;
      };
    }, [signedIn]),
  );

  if (session.status === 'unknown') {
    return (
      <ThemedView style={styles.loading}>
        <ActivityIndicator color={theme.primary} accessibilityLabel="Yükleniyor" />
      </ThemedView>
    );
  }
  if (session.status === 'signedOut') return <Redirect href="/giris" />;

  const accounts = session.customer.accounts;
  // A credit account only moves money between the customer's own accounts (see aktar.tsx), and
  // nothing leaves a frozen account.
  const senders = accounts.filter((a) => a.kind !== 'credit' && !a.frozen);
  const from = senders.find((a) => a.id === fromId) ?? senders[0];
  const iban = normalizeIban(ibanInput);
  const target: RecipientTarget =
    mode === 'iban' ? { iban } : { customerNo: customerNoInput };
  const amountKurus = parseTryAmount(amountInput);
  // Sending to one of the customer's own accounts: no cap, and the API names the account.
  const ownTarget =
    mode === 'iban'
      ? accounts.some((a) => a.iban === iban)
      : customerNoInput === session.customer.customerNo;
  // Money sent to a customer number always lands in a checking account, never a credit one.
  const ownCredit =
    mode === 'iban' ? accounts.find((a) => a.iban === iban && a.kind === 'credit') : undefined;
  const sameAccount =
    mode === 'iban'
      ? from?.iban === iban
      : ownTarget && paymentAccount(session.customer)?.id === from?.id;

  const savedMatch = saved.find((r) => sameTarget(savedTarget(r), target));

  function pickSaved(id: number) {
    const picked = saved.find((r) => r.id === id);
    if (!picked) return;
    setErrors((e) => ({ ...e, recipient: undefined }));
    if (picked.iban !== null) {
      setMode('iban');
      onIbanChange(picked.iban);
    } else {
      setMode('customerNo');
      onCustomerNoChange(picked.customerNo ?? '');
    }
  }

  async function saveCurrent() {
    const nickname = saveName.trim();
    if (saveState.status === 'saving') return;
    if (!nickname) {
      setSaveState({ status: 'error', message: 'Alıcıya bir ad verin.' });
      return;
    }
    const run = transferRun.current;
    setSaveState({ status: 'saving' });
    try {
      const row = await saveRecipient(nickname, target);
      listVersion.current++;
      // Saved either way, so the list gains it even if the user has moved on.
      setSaved((rows) => [...rows, row]);
      if (run !== transferRun.current) return;
      setSaveState({ status: 'saved' });
      AccessibilityInfo.announceForAccessibility(`${nickname} kayıtlı alıcılara eklendi.`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return void signOut();
      if (run !== transferRun.current) return;
      const message = e instanceof ApiError ? e.message : 'Alıcı kaydedilemedi.';
      setSaveState({ status: 'error', message });
      AccessibilityInfo.announceForAccessibility(message);
    }
  }

  // Each recipient is identified by a key, so an answer for an earlier input is dropped.
  const lookupKey = (to: RecipientTarget) => ('iban' in to ? `iban:${to.iban}` : `no:${to.customerNo}`);

  function changeMode(next: Mode) {
    if (next === mode) return;
    setMode(next);
    setErrors((e) => ({ ...e, recipient: undefined }));
    // The other field's recipient no longer applies; look it up again if it is complete.
    if (next === 'iban') onIbanChange(ibanInput);
    else onCustomerNoChange(customerNoInput);
  }

  function onIbanChange(text: string) {
    const cleaned = normalizeIban(text).replace(/[^A-Z0-9]/g, '').slice(0, 26);
    setIbanInput(formatIban(cleaned));
    setErrors((e) => ({ ...e, recipient: undefined }));
    latestLookup.current = lookupKey({ iban: cleaned });

    if (cleaned.length < 26) return setRecipient({ status: 'idle' });
    if (!isValidTrIban(cleaned)) {
      setRecipient({ status: 'error', message: 'IBAN hatalı görünüyor. Lütfen kontrol edin.' });
      return;
    }
    lookup({ iban: cleaned });
  }

  function onCustomerNoChange(text: string) {
    const cleaned = digitsOnly(text, 9);
    setCustomerNoInput(cleaned);
    setErrors((e) => ({ ...e, recipient: undefined }));
    latestLookup.current = lookupKey({ customerNo: cleaned });

    if (cleaned.length < 9) return setRecipient({ status: 'idle' });
    lookup({ customerNo: cleaned });
  }

  async function lookup(to: RecipientTarget) {
    const key = lookupKey(to);
    setRecipient({ status: 'checking' });
    try {
      const found = await lookupRecipient(to);
      if (latestLookup.current === key) {
        setRecipient({ status: 'found', maskedName: found.maskedName, iban: found.iban });
        AccessibilityInfo.announceForAccessibility(`Alıcı: ${found.maskedName}`);
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return void signOut();
      if (latestLookup.current === key) {
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
    if (mode === 'iban' && !isValidTrIban(iban)) next.recipient = 'Geçerli bir TR IBAN girin.';
    else if (mode === 'customerNo' && customerNoInput.length !== 9)
      next.recipient = 'Müşteri numarası 9 haneli olmalı.';
    else if (recipient.status === 'error') next.recipient = recipient.message;
    else if (recipient.status !== 'found')
      next.recipient = 'Alıcı bilgisi doğrulanıyor, lütfen bekleyin.';
    else if (from && sameAccount) next.recipient = 'Aynı hesaba para gönderilemez.';

    if (!amountInput.trim()) next.amount = 'Tutarı girin.';
    else if (amountKurus === null) next.amount = 'Tutarı 1.250,50 biçiminde girin.';
    else if (amountKurus > MAX_TRANSFER_KURUS && !ownTarget)
      next.amount = `Tek seferde en fazla ${formatKurus(MAX_TRANSFER_KURUS)} gönderebilirsiniz.`;
    else if (from && amountKurus > from.balanceKurus)
      next.amount = `Yetersiz bakiye. Kullanılabilir: ${formatKurus(from.balanceKurus)}.`;
    else if (ownCredit && amountKurus > debtKurus(ownCredit))
      next.amount =
        debtKurus(ownCredit) === 0
          ? 'Bu kredili hesapta borcunuz yok.'
          : `Ödeme borcunuzdan fazla olamaz. Borç: ${formatKurus(debtKurus(ownCredit))}.`;

    if (description.length > 140) next.description = 'Açıklama en fazla 140 karakter olabilir.';

    setErrors(next);
    const first = Object.values(next)[0];
    if (first) {
      AccessibilityInfo.announceForAccessibility(first);
      return;
    }
    // After an unclear failure the first attempt may have gone through; "Düzenle" without
    // changes must not turn the retry into a second payment.
    const contents = JSON.stringify([from?.id, target, amountKurus, description.trim()]);
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
        to: target,
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
        {saveState.status === 'saved' ? (
          <Notice tone="info">
            <ThemedText type="small">Alıcı kaydedildi. Bir dahaki sefere listeden seçebilirsiniz.</ThemedText>
          </Notice>
        ) : !ownTarget && !savedMatch ? (
          <View style={styles.field}>
            <TextField
              label="Bu alıcıyı kaydet (isteğe bağlı)"
              placeholder="Örn. Ev sahibi"
              value={saveName}
              onChangeText={(v) => {
                setSaveName(v);
                if (saveState.status === 'error') setSaveState({ status: 'idle' });
              }}
              maxLength={40}
              returnKeyType="done"
              onSubmitEditing={saveCurrent}
              error={saveState.status === 'error' ? saveState.message : undefined}
            />
            <Button
              title="Alıcıyı kaydet"
              variant="secondary"
              loading={saveState.status === 'saving'}
              onPress={saveCurrent}
            />
          </View>
        ) : null}
        <View style={styles.actions}>
          <Button title="Hesabıma dön" onPress={() => router.replace('/hesabim')} />
          <Button
            title="Yeni transfer"
            variant="secondary"
            onPress={() => {
              // A new transfer, even with identical details, must not replay the finished one.
              idempotencyKey.current = null;
              transferRun.current++;
              setStep('form');
              setResult(null);
              setIbanInput('TR');
              setCustomerNoInput('');
              setRecipient({ status: 'idle' });
              setAmountInput('');
              setDescription('');
              setSaveName('');
              setSaveState({ status: 'idle' });
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
            ...(mode === 'customerNo'
              ? ([['Alıcı müşteri no', customerNoInput]] as [string, string][])
              : []),
            ['Alıcı IBAN', formatIban(recipient.iban)],
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
          choices={senders.map((a) => ({
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

        {saved.length > 0 ? (
          <View style={styles.field}>
            <ChoiceList
              label="Kayıtlı alıcılar"
              value={savedMatch?.id ?? null}
              onChange={pickSaved}
              choices={saved.map((r) => ({
                value: r.id,
                title: r.nickname,
                detail: `${r.maskedName} · ${
                  r.iban !== null ? formatIban(r.iban) : `Müşteri no ${r.customerNo}`
                }`,
              }))}
            />
            <Pressable
              accessibilityRole="button"
              hitSlop={12}
              style={styles.link}
              onPress={() => router.push('/alicilar')}>
              <ThemedText type="label">Kayıtlı alıcıları yönet</ThemedText>
            </Pressable>
          </View>
        ) : null}

        <ChoiceList label="Alıcı" value={mode} onChange={changeMode} choices={MODES} />

        <View style={styles.field}>
          {mode === 'iban' ? (
            <TextField
              label="Alıcı IBAN"
              value={ibanInput}
              onChangeText={onIbanChange}
              autoCapitalize="characters"
              autoCorrect={false}
              autoComplete="off"
              error={
                errors.recipient ?? (recipient.status === 'error' ? recipient.message : undefined)
              }
            />
          ) : (
            <TextField
              label="Alıcı müşteri numarası"
              placeholder="9 haneli numara"
              value={customerNoInput}
              onChangeText={onCustomerNoChange}
              keyboardType="number-pad"
              autoComplete="off"
              maxLength={9}
              error={
                errors.recipient ?? (recipient.status === 'error' ? recipient.message : undefined)
              }
            />
          )}
          {recipient.status === 'checking' ? (
            <ThemedText type="small" themeColor="textSecondary">
              Alıcı doğrulanıyor…
            </ThemedText>
          ) : recipient.status === 'found' ? (
            <ThemedText type="small" accessibilityLiveRegion="polite">
              Alıcı: <ThemedText type="smallBold">{recipient.maskedName}</ThemedText>
              {mode === 'customerNo' ? ` · ${formatIban(recipient.iban)}` : ''}
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
  link: {
    alignSelf: 'flex-start',
    marginTop: Spacing.one,
  },
});
