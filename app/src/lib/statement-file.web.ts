/** Web: hands the CSV to the browser as a download. */
export async function deliverStatement(filename: string, csv: string): Promise<void> {
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  try {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    // Give the browser a moment to start the download before the URL goes away.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
