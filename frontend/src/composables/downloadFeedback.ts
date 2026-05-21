interface DownloadDialog {
  success(options: {
    title: string;
    content: string;
    positiveText?: string;
    closable?: boolean;
    maskClosable?: boolean;
  }): unknown;
}

export function showDownloadCompleteDialog(dialog: DownloadDialog, filename?: string): void {
  const safeName = filename?.trim();

  dialog.success({
    title: '下载完成',
    content: safeName ? `文件「${safeName}」已下载完成。` : '文件已下载完成。',
    positiveText: '知道了',
    closable: true,
    maskClosable: true
  });
}
