import { h, type VNodeChild } from 'vue';
import type { useDialog } from 'naive-ui';

import { openPathInFileManager } from '../api/client';

type DownloadDialog = ReturnType<typeof useDialog>;

export function showDownloadCompleteDialog(dialog: DownloadDialog, filename?: string, path?: string): void {
  const safeName = filename?.trim();
  const safePath = path?.trim();
  const content = safePath
    ? (): VNodeChild => h('div', { class: 'download-complete-content' }, [
      h('p', safeName ? `文件「${safeName}」已下载完成。` : '文件已下载完成。'),
      h('button', {
        class: 'download-path-link',
        type: 'button',
        title: safePath,
        onClick: () => void openPathInFileManager(safePath)
      }, safePath)
    ])
    : safeName ? `文件「${safeName}」已下载完成。` : '文件已下载完成。';

  dialog.success({
    title: '下载完成',
    content,
    positiveText: safePath ? '打开所在文件夹' : '知道了',
    negativeText: safePath ? '关闭' : undefined,
    closable: true,
    maskClosable: true,
    onPositiveClick: safePath ? () => openPathInFileManager(safePath) : undefined
  });
}
