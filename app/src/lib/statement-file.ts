import { File, Paths } from 'expo-file-system';
import * as Sharing from 'expo-sharing';

/** Native: writes the CSV to the cache directory and opens the share sheet (Files, Mail, …). */
export async function deliverStatement(filename: string, csv: string): Promise<void> {
  if (!(await Sharing.isAvailableAsync())) {
    throw new Error('Bu cihazda dosya paylaşımı kullanılamıyor.');
  }
  // The cache directory: the OS may clear it, and the file is rewritten on every export.
  const file = new File(Paths.cache, filename);
  file.create({ overwrite: true });
  await file.write(csv);
  await Sharing.shareAsync(file.uri, {
    mimeType: 'text/csv',
    UTI: 'public.comma-separated-values-text',
    dialogTitle: 'Ekstreyi paylaş',
  });
}
