/**
 * CapacityReport - 容量报表处理程序
 * 前端 JavaScript - TDesign 风格
 */

// ==================== 工具函数 ====================

function $(selector) {
    return document.querySelector(selector);
}

function $$(selector) {
    return document.querySelectorAll(selector);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN');
}

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        'xlsx': '📊',
        'xls': '📊',
        'csv': '📋',
        'zip': '📦'
    };
    return icons[ext] || '📄';
}

// Toast 通知
function showToast(message, type = 'info') {
    const container = $('#toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        'success': '✓',
        'error': '✕',
        'warning': '!',
        'info': 'i'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || 'i'}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" aria-label="关闭">×</button>
    `;
    container.appendChild(toast);
    
    // 触发重排，确保动画生效
    toast.offsetHeight;
    
    // 关闭函数
    const closeToast = () => {
        if (toast.timeoutId) {
            clearTimeout(toast.timeoutId);
        }
        toast.style.animation = 'toastOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    };
    
    // 绑定关闭按钮事件
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', closeToast);
    
    // 自动关闭
    toast.timeoutId = setTimeout(closeToast, 3000);
}

// 确认对话框
function showConfirm(title, message) {
    return new Promise((resolve) => {
        const modal = $('#confirmModal');
        $('#confirmTitle').textContent = title;
        $('#confirmMessage').textContent = message;
        modal.classList.add('active');
        
        const handleOk = () => {
            modal.classList.remove('active');
            cleanup();
            resolve(true);
        };
        
        const handleCancel = () => {
            modal.classList.remove('active');
            cleanup();
            resolve(false);
        };
        
        const cleanup = () => {
            $('#confirmOk').removeEventListener('click', handleOk);
            $('#confirmCancel').removeEventListener('click', handleCancel);
            modal.querySelector('.modal-backdrop').removeEventListener('click', handleCancel);
        };
        
        $('#confirmOk').addEventListener('click', handleOk);
        $('#confirmCancel').addEventListener('click', handleCancel);
        modal.querySelector('.modal-backdrop').addEventListener('click', handleCancel);
    });
}

// API 调用
async function api(endpoint, options = {}) {
    const response = await fetch(`/api${endpoint}`, {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    });
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || '请求失败');
    }
    
    return response.json();
}


// ==================== 主题管理 ====================

class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('theme') || 'light';
        this.init();
    }
    
    init() {
        // 应用保存的主题
        this.apply(this.theme);
        
        // 使用事件委托绑定所有主题切换按钮
        document.addEventListener('click', (e) => {
            if (e.target.closest('#themeToggle') || e.target.closest('#toggleThemeBtn')) {
                this.toggle();
            }
        });
        
        // 监听系统主题变化
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                this.apply(e.matches ? 'dark' : 'light');
            }
        });
    }
    
    apply(theme) {
        this.theme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        
        // 更新设置页面显示
        const themeText = $('#currentTheme');
        if (themeText) {
            themeText.textContent = theme === 'dark' ? '深色模式' : '浅色模式';
        }
    }
    
    toggle() {
        const newTheme = this.theme === 'dark' ? 'light' : 'dark';
        this.apply(newTheme);
        localStorage.setItem('theme', newTheme);
        showToast(`已切换到${newTheme === 'dark' ? '深色' : '浅色'}模式`, 'success');
    }
}


// ==================== 页面导航 ====================

class Navigation {
    constructor() {
        this.currentPage = 'upload';
        this.init();
    }
    
    init() {
        $$('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = item.dataset.page;
                this.navigate(page);
            });
        });
    }
    
    navigate(page) {
        // 更新导航状态
        $$('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === page);
        });
        
        // 切换页面
        $$('.page').forEach(p => {
            p.classList.toggle('active', p.id === `page-${page}`);
        });
        
        this.currentPage = page;
        
        // 保存当前页面到 localStorage
        localStorage.setItem('currentPage', page);
        
        // 触发页面加载事件
        window.dispatchEvent(new CustomEvent('pagechange', { detail: { page } }));
        
        // 如果导航到上传页面，检查活动任务
        if (page === 'upload') {
            const uploader = window.fileUploader;
            if (uploader && uploader.checkActiveTask) {
                uploader.checkActiveTask();
            }
        }
    }
    
    restorePage() {
        // 从 localStorage 恢复页面
        const savedPage = localStorage.getItem('currentPage');
        console.log('恢复页面:', savedPage);
        if (savedPage) {
            // 验证页面是否存在
            const pageEl = $(`#page-${savedPage}`);
            if (pageEl) {
                this.navigate(savedPage);
                return;
            }
        }
        // 如果没有保存的页面或页面不存在，确保默认显示上传页面
        // HTML 中已经设置了 upload 为默认 active，这里不需要额外操作
    }
}


// ==================== 文件上传 ====================

class FileUploader {
    constructor() {
        this.files = [];
        this.taskId = null;
        this.pollInterval = null;
        this.isUploading = false;
        this.uploadStats = {
            total: 0,
            uploading: 0,
            success: 0,
            error: 0
        };
        this.init();
    }
    
    init() {
        const uploadZone = $('#uploadZone');
        const fileInput = $('#fileInput');
        const fileInputSingle = $('#fileInputSingle');
        
        // 拖拽事件
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });
        
        uploadZone.addEventListener('drop', async (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            
            const items = e.dataTransfer.items;
            const files = [];
            
            for (let item of items) {
                if (item.kind === 'file') {
                    const entry = item.webkitGetAsEntry();
                    if (entry) {
                        await this.traverseEntry(entry, files, '');
                    }
                }
            }
            
            this.addFiles(files);
        });
        
        // 文件选择（目录）
        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files).map(f => ({
                file: f,
                path: f.webkitRelativePath || f.name
            }));
            this.addFiles(files);
            fileInput.value = '';
        });
        
        // 点击上传区域时选择文件
        uploadZone.addEventListener('click', (e) => {
            if (e.target === uploadZone || e.target.closest('.upload-icon') || e.target.closest('h3') || e.target.closest('p')) {
                fileInputSingle.click();
            }
        });
        
        fileInputSingle.addEventListener('change', (e) => {
            const files = Array.from(e.target.files).map(f => ({
                file: f,
                path: f.name
            }));
            this.addFiles(files);
            fileInputSingle.value = '';
        });
        
        // 清空按钮
        $('#clearFiles').addEventListener('click', () => {
            if (!this.isUploading) {
                this.clearFiles();
            }
        });
        
        // 上传按钮
        $('#startUpload').addEventListener('click', () => {
            this.upload();
        });
        
        // 不在页面加载时自动检查任务，只在用户导航到上传页面时检查
        // 避免无意义的轮询请求
        
        // 下载结果按钮
        $('#downloadResult').addEventListener('click', () => {
            $('#downloadModal').classList.add('active');
        });
        
        // 下载选项
        $$('.download-option').forEach(btn => {
            btn.addEventListener('click', async () => {
                const table = btn.dataset.table;
                try {
                    const response = await fetch('/api/download', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            table_name: table,
                            format: 'xlsx'
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error('下载失败');
                    }
                    
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${table}_${new Date().toISOString().slice(0, 10)}.xlsx`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                } catch (error) {
                    showToast(`下载失败: ${error.message}`, 'error');
                }
                $('#downloadModal').classList.remove('active');
            });
        });
        
        $('#downloadCancel').addEventListener('click', () => {
            $('#downloadModal').classList.remove('active');
        });
        
        // 关闭模态框点击背景
        $('#downloadModal .modal-backdrop').addEventListener('click', () => {
            $('#downloadModal').classList.remove('active');
        });
        
        // 新建任务
        $('#newProcess').addEventListener('click', () => {
            this.reset();
        });
    }
    
    async traverseEntry(entry, files, path) {
        if (entry.isFile) {
            return new Promise((resolve) => {
                entry.file((file) => {
                    const fullPath = path ? `${path}/${file.name}` : file.name;
                    files.push({ file, path: fullPath });
                    resolve();
                });
            });
        } else if (entry.isDirectory) {
            const reader = entry.createReader();
            return new Promise((resolve) => {
                reader.readEntries(async (entries) => {
                    const newPath = path ? `${path}/${entry.name}` : entry.name;
                    for (let subEntry of entries) {
                        await this.traverseEntry(subEntry, files, newPath);
                    }
                    resolve();
                });
            });
        }
    }
    
    addFiles(newFiles) {
        if (this.isUploading) return;
        
        // 过滤有效文件
        const validExtensions = ['.zip', '.xlsx', '.xls', '.csv'];
        const filtered = newFiles.filter(f => {
            const ext = '.' + f.path.split('.').pop().toLowerCase();
            return validExtensions.includes(ext);
        }).map(f => ({
            ...f,
            status: 'pending', // pending, uploading, uploaded, error
            progress: 0
        }));
        
        this.files.push(...filtered);
        this.updateFileList();
    }
    
    updateFileList() {
        const fileList = $('#fileList');
        const fileItems = $('#fileItems');
        const fileCount = $('#fileCount');
        
        if (this.files.length === 0) {
            fileList.style.display = 'none';
            return;
        }
        
        fileList.style.display = 'block';
        fileItems.innerHTML = this.files.map((f, i) => `
            <div class="file-item ${f.status}" data-index="${i}" id="file-item-${i}">
                <span class="file-item-icon">${getFileIcon(f.path)}</span>
                <span class="file-item-name" title="${f.path}">${f.path}</span>
                <span class="file-item-size">${formatFileSize(f.file.size)}</span>
                <span class="file-item-status ${f.status}">
                    ${this.getStatusText(f.status, f.progress)}
                </span>
                ${f.status !== 'pending' ? `
                    <div class="file-progress">
                        <div class="file-progress-bar" style="width: ${f.progress}%"></div>
                    </div>
                ` : ''}
            </div>
        `).join('');
        
        fileCount.textContent = `${this.files.length} 个文件`;
    }
    
    getStatusText(status, progress) {
        switch (status) {
            case 'pending': return '等待上传';
            case 'uploading': return `上传中 ${progress}%`;
            case 'uploaded': return '✓ 已完成';
            case 'error': return '✕ 失败';
            default: return '';
        }
    }
    
    updateFileStatus(index, status, progress = 0) {
        if (this.files[index]) {
            this.files[index].status = status;
            this.files[index].progress = progress;
            
            const fileItem = $(`#file-item-${index}`);
            if (fileItem) {
                // 更新样式类
                fileItem.className = `file-item ${status}`;
                fileItem.dataset.index = index;
                fileItem.id = `file-item-${index}`;
                
                // 更新状态文本
                const statusEl = fileItem.querySelector('.file-item-status');
                if (statusEl) {
                    statusEl.className = `file-item-status ${status}`;
                    statusEl.textContent = this.getStatusText(status, progress);
                }
                
                // 更新或创建进度条
                let progressEl = fileItem.querySelector('.file-progress');
                if (status !== 'pending') {
                    if (!progressEl) {
                        progressEl = document.createElement('div');
                        progressEl.className = 'file-progress';
                        progressEl.innerHTML = '<div class="file-progress-bar"></div>';
                        fileItem.appendChild(progressEl);
                    }
                    progressEl.querySelector('.file-progress-bar').style.width = `${progress}%`;
                }
                
                // 自动滚动到当前上传的文件
                if (status === 'uploading') {
                    fileItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        }
    }
    
    updateUploadStats() {
        const stats = {
            total: this.files.length,
            uploading: this.files.filter(f => f.status === 'uploading').length,
            success: this.files.filter(f => f.status === 'uploaded').length,
            error: this.files.filter(f => f.status === 'error').length
        };
        
        $('#statsTotal').textContent = stats.total;
        $('#statsUploading').textContent = stats.uploading;
        $('#statsSuccess').textContent = stats.success;
        $('#statsError').textContent = stats.error;
        
        // 更新总进度
        const totalProgress = Math.round((stats.success + stats.error) / stats.total * 100);
        $('#totalPercent').textContent = `${totalProgress}%`;
        $('#totalProgressBar').style.width = `${totalProgress}%`;
    }
    
    clearFiles() {
        this.files = [];
        this.updateFileList();
        $('#totalProgress').style.display = 'none';
        $('#uploadStats').style.display = 'none';
    }
    
    async upload() {
        if (this.files.length === 0) {
            showToast('请先选择文件', 'warning');
            return;
        }
        
        if (this.isUploading) {
            showToast('正在上传中，请稍候', 'warning');
            return;
        }
        
        // 检查是否有其他任务在运行
        try {
            const statusCheck = await api('/task/status');
            if (statusCheck.has_active) {
                const stageText = statusCheck.stage === 'uploading' ? '上传' : '处理';
                showToast(`已有任务在运行（${stageText}中）`, 'warning');
                // 显示当前任务状态
                this.taskId = statusCheck.task_id;
                $('#uploadZone').style.display = 'none';
                $('#fileList').style.display = 'none';
                $('#processSection').style.display = 'block';
                $('#processActions').style.display = 'none';
                $('#processStatus').className = 'process-status processing';
                $('#processStatus').textContent = statusCheck.stage === 'uploading' ? '上传中...' : '处理中...';
                if (statusCheck.logs && statusCheck.logs.length > 0) {
                    const logContent = $('#logContent');
                    logContent.innerHTML = statusCheck.logs.map(log => {
                        let level = 'info';
                        if (log.includes('[SUCCESS]')) level = 'success';
                        else if (log.includes('[ERROR]')) level = 'error';
                        else if (log.includes('[WARN]')) level = 'warn';
                        return `<div class="log-line ${level}">${log}</div>`;
                    }).join('');
                }
                if (statusCheck.stage === 'processing') {
                    this.pollStatus();
                } else {
                    this.pollGlobalStatus();
                }
                return;
            }
        } catch (error) {
            console.error('检查任务状态失败:', error);
        }
        
        // 立即更新UI状态（在开始上传前）
        // 隐藏上传区域和文件列表
        $('#uploadZone').style.display = 'none';
        $('#fileList').style.display = 'none';
        $('#totalProgress').style.display = 'none';
        $('#uploadStats').style.display = 'none';
        
        // 显示处理区域（上传中状态）
        $('#processSection').style.display = 'block';
        $('#processActions').style.display = 'none';
        $('#logContent').innerHTML = '<div class="log-line info">正在上传文件...</div>';
        $('#processStatus').className = 'process-status processing';
        $('#processStatus').textContent = '上传中...';
        
        // 强制浏览器重绘
        $('#processSection').offsetHeight;
        
        this.isUploading = true;
        $('#startUpload').disabled = true;
        $('#clearFiles').disabled = true;
        
        showToast('开始批量上传文件...', 'info');
        
        try {
            // 创建 FormData，添加所有文件
            const formData = new FormData();
            this.files.forEach(fileData => {
                formData.append('files', fileData.file, fileData.path);
            });
            
            // 使用 XMLHttpRequest 来跟踪上传进度
            const result = await new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                
                // 上传进度事件
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const progress = Math.round((e.loaded / e.total) * 100);
                        // 更新日志显示进度
                        $('#logContent').innerHTML = `<div class="log-line info">正在上传文件... ${progress}%</div>`;
                        $('#processStatus').textContent = `上传中 ${progress}%`;
                    }
                });
                
                // 完成事件
                xhr.addEventListener('load', () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            const result = JSON.parse(xhr.responseText);
                            resolve(result);
                        } catch {
                            resolve({ success: true });
                        }
                    } else {
                        reject(new Error('上传失败'));
                    }
                });
                
                // 错误事件
                xhr.addEventListener('error', () => {
                    reject(new Error('网络错误'));
                });
                
                // 开始上传
                xhr.open('POST', '/api/upload');
                xhr.send(formData);
            });
            
            // 上传成功，获取后端返回的任务ID
            const taskId = result.task_id || result.session_id;
            if (!taskId) {
                throw new Error('未获取到任务ID');
            }
            
            this.taskId = taskId;
            console.log('上传完成，任务ID:', taskId);
            
            // 注意：锁定已在后端上传接口中完成，这里不需要再次锁定
            
            // 更新UI显示上传完成
            $('#logContent').innerHTML = `<div class="log-line success">上传完成: ${result.file_count || this.files.length} 个文件</div>`;
            $('#processStatus').textContent = '准备开始处理...';
            showToast(`上传完成: ${result.file_count || this.files.length} 个文件`, 'success');
            
            // 立即开始处理（不等待）
            console.log('开始启动处理任务...');
            this.startProcessing().catch(error => {
                console.error('启动处理失败:', error);
                showToast(`启动处理失败: ${error.message}`, 'error');
                // 如果启动失败，恢复显示上传区域
                $('#processSection').style.display = 'none';
                this.restoreUploadUI();
            });
            
        } catch (error) {
            showToast(`上传失败: ${error.message}`, 'error');
            console.error('上传失败:', error);
            // 上传失败，解锁全局任务（后端会自动处理，但这里也尝试解锁）
            if (this.taskId) {
                try {
                    await api('/task/unlock', {
                        method: 'POST',
                        body: JSON.stringify({ task_id: this.taskId })
                    });
                } catch (unlockError) {
                    console.error('解锁任务失败:', unlockError);
                }
            }
            // 恢复显示上传区域
            $('#processSection').style.display = 'none';
            this.restoreUploadUI();
        } finally {
            this.isUploading = false;
            $('#startUpload').disabled = false;
            $('#clearFiles').disabled = false;
        }
    }
    
    async startProcessing() {
        if (!this.taskId) {
            console.error('startProcessing: taskId 为空');
            return;
        }
        
        console.log('startProcessing: 开始启动处理，taskId =', this.taskId);
        
        try {
            // 更新UI状态
            $('#processStatus').textContent = '正在启动处理...';
            $('#logContent').innerHTML = '<div class="log-line info">正在启动数据处理任务...</div>';
            
            const response = await api('/process/start', { 
                method: 'POST',
                body: JSON.stringify({ task_id: this.taskId })
            });
            
            console.log('startProcessing: 处理任务已启动，响应:', response);
            
            // 显示处理区域
            $('#processSection').style.display = 'block';
            $('#processActions').style.display = 'none';
            $('#processStatus').className = 'process-status processing';
            $('#processStatus').textContent = '处理中...';
            $('#logContent').innerHTML = '<div class="log-line info">处理任务已启动，等待日志...</div>';
            
            // 确保上传区域和文件列表保持隐藏
            $('#uploadZone').style.display = 'none';
            $('#fileList').style.display = 'none';
            
            // 开始轮询状态（延迟一点，确保后端已经开始处理）
            setTimeout(() => {
                this.pollStatus();
            }, 500);
            
        } catch (error) {
            console.error('startProcessing: 启动处理失败:', error);
            showToast(`启动处理失败: ${error.message}`, 'error');
            // 如果启动失败，恢复显示上传区域
            $('#processSection').style.display = 'none';
            this.restoreUploadUI();
            // 解锁全局任务
            if (this.taskId) {
                try {
                    await api('/task/unlock', {
                        method: 'POST',
                        body: JSON.stringify({ task_id: this.taskId })
                    });
                } catch (unlockError) {
                    console.error('解锁任务失败:', unlockError);
                }
            }
        }
    }
    
    pollStatus() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        
        if (!this.taskId) {
            console.error('轮询状态失败: taskId 为空');
            this.restoreUploadUI();
            return;
        }
        
        console.log('开始轮询任务状态:', this.taskId);
        
        // 绑定手动刷新按钮
        const manualRefreshBtn = $('#manualRefreshLog');
        if (manualRefreshBtn) {
            manualRefreshBtn.onclick = () => {
                this.refreshLogOnce();
            };
        }
        
        // 监听自动刷新开关变化
        const autoRefreshCheckbox = $('#autoRefreshLog');
        if (autoRefreshCheckbox) {
            autoRefreshCheckbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    // 开启自动刷新，重新开始轮询
                    if (!this.pollInterval) {
                        this.pollStatus();
                    }
                } else {
                    // 关闭自动刷新，停止轮询
                    if (this.pollInterval) {
                        clearInterval(this.pollInterval);
                        this.pollInterval = null;
                        console.log('已停止自动刷新轮询');
                    }
                }
            });
        }
        
        const poll = async () => {
            try {
                // 检查自动刷新开关
                const autoRefreshCheckbox = $('#autoRefreshLog');
                if (autoRefreshCheckbox && !autoRefreshCheckbox.checked) {
                    // 如果关闭了自动刷新，停止轮询
                    if (this.pollInterval) {
                        clearInterval(this.pollInterval);
                        this.pollInterval = null;
                    }
                    return;
                }
                const status = await api('/process/status', { 
                    method: 'POST',
                    body: JSON.stringify({ task_id: this.taskId })
                });
                
                // 更新日志
                const logContent = $('#logContent');
                if (status.logs && status.logs.length > 0) {
                    logContent.innerHTML = status.logs.map(log => {
                        let level = 'info';
                        if (log.includes('[SUCCESS]')) level = 'success';
                        else if (log.includes('[ERROR]')) level = 'error';
                        else if (log.includes('[WARN]')) level = 'warn';
                        return `<div class="log-line ${level}">${log}</div>`;
                    }).join('');
                }
                
                // 自动滚动到底部（仅在自动刷新开启时）
                if (autoRefreshCheckbox && autoRefreshCheckbox.checked) {
                    const container = $('#logContainer');
                    container.scrollTop = container.scrollHeight;
                }
                
                // 更新状态
                const statusEl = $('#processStatus');
                if (status.status === 'completed') {
                    statusEl.textContent = '处理完成';
                    statusEl.className = 'process-status completed';
                    $('#processActions').style.display = 'flex';
                    // 任务完成，立即停止轮询
                    if (this.pollInterval) {
                        clearInterval(this.pollInterval);
                        this.pollInterval = null;
                    }
                    showToast('数据处理完成！', 'success');
                    // 任务完成，不立即恢复上传区域，让用户查看结果
                    // 用户可以通过点击"新任务"按钮或切换页面来重置
                    this.files = [];  // 清空已上传的文件
                } else if (status.status === 'failed') {
                    statusEl.textContent = '处理失败';
                    statusEl.className = 'process-status failed';
                    $('#processActions').style.display = 'flex';
                    // 任务失败，立即停止轮询
                    if (this.pollInterval) {
                        clearInterval(this.pollInterval);
                        this.pollInterval = null;
                    }
                    showToast('数据处理失败', 'error');
                    // 任务失败，不立即恢复上传区域
                    this.files = [];
                } else {
                    statusEl.textContent = '处理中...';
                    statusEl.className = 'process-status processing';
                }
                
            } catch (error) {
                console.error('轮询状态失败:', error);
                // 如果请求失败（如 404），可能是任务ID错误
                if (error.message && error.message.includes('404')) {
                    clearInterval(this.pollInterval);
                    showToast('任务状态获取失败', 'error');
                    $('#processStatus').textContent = '状态获取失败';
                    $('#processStatus').className = 'process-status failed';
                    this.restoreUploadUI();
                }
            }
        };
        
        poll();
        this.pollInterval = setInterval(poll, 1000);
    }
    
    async refreshLogOnce() {
        if (!this.taskId) return;
        
        try {
            const status = await api('/process/status', { 
                method: 'POST',
                body: JSON.stringify({ task_id: this.taskId })
            });
            
            // 更新日志
            const logContent = $('#logContent');
            if (status.logs && status.logs.length > 0) {
                logContent.innerHTML = status.logs.map(log => {
                    let level = 'info';
                    if (log.includes('[SUCCESS]')) level = 'success';
                    else if (log.includes('[ERROR]')) level = 'error';
                    else if (log.includes('[WARN]')) level = 'warn';
                    return `<div class="log-line ${level}">${log}</div>`;
                }).join('');
            }
            
            // 不自动滚动，让用户自己控制
        } catch (error) {
            console.error('手动刷新日志失败:', error);
        }
    }
    
    restoreUploadUI() {
        // 恢复显示上传区域（使用 flex 布局）
        $('#uploadZone').style.display = 'flex';
        // 只有当有文件时才显示文件列表
        if (this.files.length > 0) {
            $('#fileList').style.display = 'block';
        }
        // 隐藏进度和统计
        $('#totalProgress').style.display = 'none';
        $('#uploadStats').style.display = 'none';
        this.isUploading = false;
        $('#startUpload').disabled = false;
        $('#clearFiles').disabled = false;
    }
    
    reset() {
        this.files = [];
        this.taskId = null;
        this.isUploading = false;
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        
        this.updateFileList();
        // 隐藏处理区域
        $('#processSection').style.display = 'none';
        $('#processActions').style.display = 'none';
        $('#processStatus').className = 'process-status processing';
        $('#processStatus').textContent = '处理中...';
        $('#logContent').innerHTML = '';
        // 恢复显示上传区域
        this.restoreUploadUI();
        console.log('任务已重置，UI 已恢复');
    }
    
    async checkActiveTask() {
        // 检查是否有正在进行的任务（全局状态）
        // 只在用户导航到上传页面时调用，避免无意义的请求
        try {
            const result = await api('/task/status');
            if (result.has_active) {
                // 有任务正在进行，隐藏上传区域，显示处理进度
                $('#uploadZone').style.display = 'none';
                $('#fileList').style.display = 'none';
                $('#totalProgress').style.display = 'none';
                $('#uploadStats').style.display = 'none';
                this.taskId = result.task_id;
                $('#processSection').style.display = 'block';
                $('#processActions').style.display = 'none';
                $('#processStatus').className = 'process-status processing';
                
                // 根据阶段显示不同状态
                const stageText = result.stage === 'uploading' ? '上传中...' : '处理中...';
                $('#processStatus').textContent = stageText;
                
                // 显示已有的日志
                if (result.logs && result.logs.length > 0) {
                    const logContent = $('#logContent');
                    logContent.innerHTML = result.logs.map(log => {
                        let level = 'info';
                        if (log.includes('[SUCCESS]')) level = 'success';
                        else if (log.includes('[ERROR]')) level = 'error';
                        else if (log.includes('[WARN]')) level = 'warn';
                        return `<div class="log-line ${level}">${log}</div>`;
                    }).join('');
                    const container = $('#logContainer');
                    container.scrollTop = container.scrollHeight;
                } else if (result.stage === 'uploading') {
                    $('#logContent').innerHTML = '<div class="log-line info">正在上传文件...</div>';
                } else {
                    $('#logContent').innerHTML = '';
                }
                
                // 只有在处理中且自动刷新开启时才开始轮询
                // 避免多人同时轮询导致并发过大
                if (result.stage === 'processing') {
                    const autoRefreshCheckbox = $('#autoRefreshLog');
                    if (autoRefreshCheckbox && autoRefreshCheckbox.checked) {
                        this.pollStatus();
                    }
                } else if (result.stage === 'uploading') {
                    // 上传中，轮询全局状态（但也要检查自动刷新）
                    const autoRefreshCheckbox = $('#autoRefreshLog');
                    if (autoRefreshCheckbox && autoRefreshCheckbox.checked) {
                        this.pollGlobalStatus();
                    }
                }
            }
        } catch (error) {
            console.error('检查活动任务失败:', error);
        }
    }
    
    pollGlobalStatus() {
        // 轮询全局任务状态（用于等待上传完成）
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        
        const poll = async () => {
            try {
                // 检查自动刷新开关，如果关闭则停止轮询
                const autoRefreshCheckbox = $('#autoRefreshLog');
                if (autoRefreshCheckbox && !autoRefreshCheckbox.checked) {
                    if (this.pollInterval) {
                        clearInterval(this.pollInterval);
                        this.pollInterval = null;
                    }
                    return;
                }
                
                const result = await api('/task/status');

                if (!result.has_active) {
                    // 任务已完成或取消，停止轮询并恢复上传界面
                    if (this.pollInterval) {
                        clearInterval(this.pollInterval);
                        this.pollInterval = null;
                    }
                    $('#processSection').style.display = 'none';
                    this.restoreUploadUI();
                    showToast('任务已完成', 'info');
                } else if (result.stage === 'processing') {
                    // 转为处理中状态，切换到处理轮询
                    if (this.pollInterval) {
                        clearInterval(this.pollInterval);
                        this.pollInterval = null;
                    }
                    this.taskId = result.task_id;
                    $('#processStatus').textContent = '处理中...';
                    // 只有自动刷新开启时才继续轮询
                    if (autoRefreshCheckbox && autoRefreshCheckbox.checked) {
                        this.pollStatus();
                    }
                } else {
                    // 仍在上传中
                    $('#processStatus').textContent = '上传中...';
                }
            } catch (error) {
                console.error('轮询全局状态失败:', error);
            }
        };
        
        poll();
        this.pollInterval = setInterval(poll, 1000);
    }
}


// ==================== 历史记录 ====================

class HistoryManager {
    constructor() {
        this.init();
    }
    
    init() {
        $('#refreshHistory').addEventListener('click', () => this.load());
        $('#clearHistory').addEventListener('click', () => this.clear());
        
        window.addEventListener('pagechange', (e) => {
            if (e.detail.page === 'history') {
                this.load();
            }
        });
    }
    
    async load() {
        const container = $('#historyList');
        container.innerHTML = '<div class="loading">加载中...</div>';
        
        try {
            const data = await api('/history', { method: 'POST' });
            
            if (data.records.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <span class="empty-icon">📭</span>
                        <p>暂无处理记录</p>
                    </div>
                `;
                // 即使没有历史记录，也要加载总占用大小
                this.loadTotalSize();
                return;
            }
            
            container.innerHTML = data.records.map(record => `
                <div class="history-item" data-id="${record.id}">
                    <div class="history-status ${record.status}"></div>
                    <div class="history-info">
                        <div class="history-id">${record.id}</div>
                        <div class="history-meta">
                            ${formatDateTime(record.timestamp)} · 
                            ${record.file_count} 个文件 · 
                            ${record.elapsed_time ? record.elapsed_time + ' 秒' : '-'} · 
                            <span class="record-size" data-id="${record.id}">计算中...</span>
                        </div>
                    </div>
                    <div class="history-actions">
                        <button class="btn btn-sm btn-outline view-log" data-id="${record.id}">
                            📋 日志
                        </button>
                        <button class="btn btn-sm btn-danger delete-record" data-id="${record.id}">
                            🗑️
                        </button>
                    </div>
                </div>
            `).join('');
            
            // 加载每个记录的占用大小
            container.querySelectorAll('.record-size').forEach(el => {
                this.loadRecordSize(el.dataset.id, el);
            });
            
            // 加载总占用大小
            this.loadTotalSize();
            
            // 绑定事件
            container.querySelectorAll('.view-log').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.viewLog(btn.dataset.id);
                });
            });
            
            container.querySelectorAll('.delete-record').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.delete(btn.dataset.id);
                });
            });
            
        } catch (error) {
            container.innerHTML = `<div class="empty-state"><p>加载失败: ${error.message}</p></div>`;
        }
    }
    
    async viewLog(id) {
        try {
            const record = await api('/history/detail', { 
                method: 'POST',
                body: JSON.stringify({ record_id: id })
            });
            
            // 使用模态框显示日志
            const modal = document.createElement('div');
            modal.className = 'modal active';
            modal.innerHTML = `
                <div class="modal-backdrop"></div>
                <div class="modal-content" style="width: 800px; max-height: 80vh;">
                    <h3>处理日志 - ${id}</h3>
                    <div class="log-container" style="height: 400px; margin-bottom: 16px;">
                        <div class="log-content">
                            ${record.logs.map(log => {
                                let level = 'info';
                                if (log.includes('[SUCCESS]')) level = 'success';
                                else if (log.includes('[ERROR]')) level = 'error';
                                else if (log.includes('[WARN]')) level = 'warn';
                                return `<div class="log-line ${level}">${log}</div>`;
                            }).join('')}
                        </div>
                    </div>
                    <div class="modal-actions">
                        <button class="btn btn-outline close-modal">关闭</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            modal.querySelector('.close-modal').addEventListener('click', () => modal.remove());
            modal.querySelector('.modal-backdrop').addEventListener('click', () => modal.remove());
            
        } catch (error) {
            showToast(`加载日志失败: ${error.message}`, 'error');
        }
    }
    
    async delete(id) {
        const confirmed = await showConfirm('删除记录', '确定要删除这条历史记录吗？');
        if (!confirmed) return;
        
        try {
            await api('/history/delete', { method: 'POST', body: JSON.stringify({ record_id: id }) });
            showToast('删除成功', 'success');
            this.load();
        } catch (error) {
            showToast(`删除失败: ${error.message}`, 'error');
        }
    }
    
    async clear() {
        const confirmed = await showConfirm('清空历史', '确定要清空所有历史记录吗？此操作不可恢复。');
        if (!confirmed) return;
        
        try {
            await api('/history/clear', { method: 'POST' });
            showToast('已清空所有历史记录', 'success');
            this.load();
        } catch (error) {
            showToast(`清空失败: ${error.message}`, 'error');
        }
    }
    
    async loadRecordSize(recordId, element) {
        try {
            const result = await api('/history/size', {
                method: 'POST',
                body: JSON.stringify({ record_id: recordId })
            });
            if (result.success) {
                element.textContent = result.size_formatted;
            } else {
                element.textContent = '计算失败';
            }
        } catch (error) {
            element.textContent = '计算失败';
        }
    }
    
    async loadTotalSize() {
        const totalSizeEl = $('#totalHistorySize');
        if (!totalSizeEl) return;
        
        try {
            const result = await api('/cache/size');
            if (result.success) {
                totalSizeEl.textContent = result.size_formatted;
            } else {
                totalSizeEl.textContent = '计算失败';
            }
        } catch (error) {
            totalSizeEl.textContent = '计算失败';
        }
    }
}


// ==================== 数据库管理 ====================

class DatabaseManager {
    constructor() {
        this.currentTable = null;
        this.currentPage = 1;
        this.pageSize = 50;
        this.totalPages = 1;
        this.columns = [];
        this.init();
    }
    
    init() {
        $('#downloadTable').addEventListener('click', () => this.downloadTable());
        $('#truncateTable').addEventListener('click', () => this.truncateTable());
        $('#dropTable').addEventListener('click', () => this.dropTable());
        $('#dropAllTables').addEventListener('click', () => this.dropAllTables());
        
        // 分页按钮事件
        $('#firstPage').addEventListener('click', () => this.goToPage(1));
        $('#prevPage').addEventListener('click', () => this.goToPage(this.currentPage - 1));
        $('#nextPage').addEventListener('click', () => this.goToPage(this.currentPage + 1));
        $('#lastPage').addEventListener('click', () => this.goToPage(this.totalPages));
        
        // 页面大小选择
        $('#pageSizeSelect').addEventListener('change', (e) => {
            this.pageSize = parseInt(e.target.value);
            this.currentPage = 1;
            this.loadData();
        });
        
        // 跳转页面输入框
        $('#pageJumpInput').addEventListener('keyup', (e) => {
            if (e.key === 'Enter') {
                const page = parseInt(e.target.value);
                if (page >= 1 && page <= this.totalPages) {
                    this.goToPage(page);
                } else {
                    e.target.value = this.currentPage;
                    showToast(`页码必须在 1-${this.totalPages} 之间`, 'error');
                }
            }
        });
        
        // 失去焦点时恢复当前页
        $('#pageJumpInput').addEventListener('blur', (e) => {
            e.target.value = this.currentPage;
        });
        
        window.addEventListener('pagechange', (e) => {
            if (e.detail.page === 'database') {
                this.testConnection();
                this.loadTables();
            }
        });
    }
    
    async testConnection() {
        const versionEl = $('#dbVersion');
        if (!versionEl) return;
        
        const versionBadge = versionEl.querySelector('.version-badge');
        if (!versionBadge) return;
        
        versionBadge.classList.remove('connected', 'error', 'unknown');
        versionBadge.classList.add('unknown');
        versionBadge.textContent = '检测中';
        
        try {
            const result = await api('/database/test', { method: 'POST' });

            if (result.success) {
                // 连接成功，加载服务器信息
                await this.loadServerInfo();
            } else {
                // 连接失败
                versionBadge.classList.remove('unknown');
                versionBadge.classList.add('error');
                versionBadge.textContent = '连接失败';
                versionBadge.title = result.message || '无法连接到数据库';
            }
        } catch (error) {
            // 连接异常
            versionBadge.classList.remove('unknown');
            versionBadge.classList.add('error');
            versionBadge.textContent = '连接失败';
            versionBadge.title = error.message || '连接异常';
        }
    }
    
    async loadServerInfo() {
        const versionEl = $('#dbVersion');
        const loadDataEl = $('#loadDataSupport');
        
        if (!versionEl || !loadDataEl) return;
        
        try {
            const info = await api('/database/info');
            
            if (info.success) {
                // 显示版本（连接成功）
                const versionBadge = versionEl.querySelector('.version-badge');
                versionBadge.classList.remove('unknown', 'error');
                versionBadge.classList.add('connected');
                versionBadge.textContent = info.version || '-';
                versionBadge.title = '数据库版本';
                
                // 显示 LOAD DATA INFILE 支持状态
                const badge = loadDataEl.querySelector('.support-badge');
                badge.classList.remove('unknown', 'supported', 'unsupported');
                
                if (info.load_data_infile) {
                    badge.classList.add('supported');
                    badge.textContent = '已启用';
                    badge.title = info.load_data_message || '支持高速导入';
                } else {
                    badge.classList.add('unsupported');
                    badge.textContent = '未启用';
                    badge.title = info.load_data_message || '将使用标准导入模式';
                }
            } else {
                // 获取信息失败，但连接可能成功
                const versionBadge = versionEl.querySelector('.version-badge');
                versionBadge.classList.remove('unknown');
                versionBadge.classList.add('error');
                versionBadge.textContent = '获取失败';
                versionBadge.title = info.error || '无法获取服务器信息';
            }
        } catch (error) {
            console.error('获取服务器信息失败:', error);
            const versionBadge = versionEl.querySelector('.version-badge');
            versionBadge.classList.remove('unknown');
            versionBadge.classList.add('error');
            versionBadge.textContent = '获取失败';
            versionBadge.title = error.message || '获取服务器信息异常';
        }
    }
    
    async loadTables() {
        const container = $('#tableList');
        container.innerHTML = '<div class="loading">加载中...</div>';
        
        try {
            const data = await api('/database/tables');
            
            if (data.tables.length === 0) {
                container.innerHTML = '<div class="empty-state" style="padding: 24px;"><p>暂无数据表</p></div>';
                return;
            }
            
            container.innerHTML = data.tables.map(table => `
                <div class="table-item" data-table="${table}">
                    <span class="table-icon">📊</span>
                    <span>${table}</span>
                </div>
            `).join('');
            
            container.querySelectorAll('.table-item').forEach(item => {
                item.addEventListener('click', () => {
                    container.querySelectorAll('.table-item').forEach(i => i.classList.remove('active'));
                    item.classList.add('active');
                    this.selectTable(item.dataset.table);
                });
            });
            
        } catch (error) {
            container.innerHTML = `<div class="empty-state" style="padding: 24px;"><p>加载失败</p></div>`;
        }
    }
    
    async selectTable(tableName) {
        this.currentTable = tableName;
        this.currentPage = 1;
        
        // 重置页面大小为默认值
        $('#pageSizeSelect').value = this.pageSize.toString();
        $('#pageJumpInput').value = '1';
        
        $('#dbToolbar').style.display = 'flex';
        $('#currentTable').textContent = tableName;
        $('#pagination').style.display = 'flex';
        
        try {
            const info = await api('/database/table/info', {
                method: 'POST',
                body: JSON.stringify({ table_name: tableName })
            });
            this.columns = info.columns.map(c => c.Field);
            $('#rowCount').textContent = `${info.row_count} 行`;
            
            await this.loadData();
            
        } catch (error) {
            showToast(`加载表信息失败: ${error.message}`, 'error');
        }
    }
    
    goToPage(page) {
        if (page < 1) page = 1;
        if (page > this.totalPages) page = this.totalPages;
        if (page === this.currentPage) return;
        
        this.currentPage = page;
        this.loadData();
    }
    
    async loadData() {
        const container = $('#dataTableContainer');
        container.innerHTML = '<div class="loading">加载中...</div>';
        
        try {
            const result = await api('/database/table/data', {
                method: 'POST',
                body: JSON.stringify({
                    table_name: this.currentTable,
                    page: this.currentPage,
                    page_size: this.pageSize
                })
            });
            
            this.totalPages = result.total_pages;
            this.renderTable(result.data);
            
            // 更新分页信息
            $('#totalRecords').textContent = result.total;
            $('#totalPagesDisplay').textContent = this.totalPages;
            $('#pageJumpInput').value = this.currentPage;
            $('#pageJumpInput').max = this.totalPages;
            
            // 更新按钮状态
            $('#firstPage').disabled = this.currentPage <= 1;
            $('#prevPage').disabled = this.currentPage <= 1;
            $('#nextPage').disabled = this.currentPage >= this.totalPages;
            $('#lastPage').disabled = this.currentPage >= this.totalPages;
            
        } catch (error) {
            container.innerHTML = `<div class="empty-state"><p>加载失败: ${error.message}</p></div>`;
        }
    }
    
    renderTable(data) {
        const container = $('#dataTableContainer');
        
        // 使用已保存的字段列表，如果没有则从数据中获取
        const columns = this.columns && this.columns.length > 0 
            ? this.columns 
            : (data.length > 0 ? Object.keys(data[0]) : []);
        
        if (columns.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>暂无数据</p></div>';
            return;
        }
        
        container.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        ${columns.map(col => `<th>${col}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${data.length === 0 ? `
                        <tr class="empty-row">
                            <td colspan="${columns.length}" style="text-align: center; padding: 40px; color: var(--td-text-color-placeholder);">
                                <div class="empty-state" style="padding: 0;">
                                    <p>暂无数据</p>
                                </div>
                            </td>
                        </tr>
                    ` : data.map(row => `
                        <tr>
                            ${columns.map(col => `<td title="${row[col] || ''}">${row[col] ?? ''}</td>`).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }
    
    async downloadTable() {
        if (!this.currentTable) return;
        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    table_name: this.currentTable,
                    format: 'xlsx'
                })
            });
            
            if (!response.ok) {
                throw new Error('下载失败');
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${this.currentTable}_${new Date().toISOString().slice(0, 10)}.xlsx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            showToast(`下载失败: ${error.message}`, 'error');
        }
    }
    
    async truncateTable() {
        if (!this.currentTable) return;
        
        const confirmed = await showConfirm('清空表', `确定要清空表 "${this.currentTable}" 的所有数据吗？此操作不可恢复。`);
        if (!confirmed) return;
        
        try {
            await api('/database/table/truncate', {
                method: 'POST',
                body: JSON.stringify({ table_name: this.currentTable })
            });
            showToast('表已清空', 'success');
            this.loadData();
        } catch (error) {
            showToast(`清空失败: ${error.message}`, 'error');
        }
    }
    
    async dropTable() {
        if (!this.currentTable) return;
        
        const confirmed = await showConfirm('删除表', `确定要删除表 "${this.currentTable}" 吗？此操作不可恢复。`);
        if (!confirmed) return;
        
        try {
            await api('/database/table/drop', {
                method: 'POST',
                body: JSON.stringify({ table_name: this.currentTable })
            });
            showToast('表已删除', 'success');
            this.currentTable = null;
            $('#dbToolbar').style.display = 'none';
            $('#pagination').style.display = 'none';
            $('#dataTableContainer').innerHTML = '<div class="empty-state"><span class="empty-icon">👈</span><p>请选择左侧的数据表</p></div>';
            this.loadTables();
        } catch (error) {
            showToast(`删除失败: ${error.message}`, 'error');
        }
    }
    
    async dropAllTables() {
        // 首先获取所有表
        let tables = [];
        try {
            const result = await api('/database/tables', { method: 'POST' });
            tables = result.tables || [];
        } catch (error) {
            showToast(`获取表列表失败: ${error.message}`, 'error');
            return;
        }
        
        if (tables.length === 0) {
            showToast('数据库中没有表', 'info');
            return;
        }
        
        // 第一次确认
        const firstConfirm = await showConfirm(
            '删除全部表',
            `警告：此操作将删除数据库中的所有 ${tables.length} 个表！\n\n表列表：${tables.slice(0, 10).join(', ')}${tables.length > 10 ? '...' : ''}\n\n此操作不可恢复，请谨慎操作！`
        );
        
        if (!firstConfirm) return;
        
        // 第二次确认（双重确认，防止误操作）
        const secondConfirm = await showConfirm(
            '最后确认',
            `您确定要删除所有 ${tables.length} 个表吗？\n\n此操作将永久删除所有数据，无法恢复！\n\n请再次确认。`
        );
        
        if (!secondConfirm) return;
        
        // 执行删除
        try {
            const result = await api('/database/table/drop-all', {
                method: 'POST'
            });
            
            showToast(`已删除 ${result.dropped_count} 个表`, 'success');
            
            // 重置当前状态
            this.currentTable = null;
            $('#dbToolbar').style.display = 'none';
            $('#pagination').style.display = 'none';
            $('#dataTableContainer').innerHTML = '<div class="empty-state"><span class="empty-icon">📭</span><p>数据库中没有表</p></div>';
            
            // 重新加载表列表
            this.loadTables();
        } catch (error) {
            showToast(`删除失败: ${error.message}`, 'error');
        }
    }
}


// ==================== 设置管理 ====================

class SettingsManager {
    constructor() {
        this.sheetFilters = [];
        this.extractFields = [];
        this.fieldSearchKeyword = '';
        this.init();
    }
    
    init() {
        // 数据库配置保存
        $('#saveMysqlConfig').addEventListener('click', () => this.saveMysqlConfig());
        $('#testDbConnection').addEventListener('click', () => this.testConnection());
        
        // 密码显示/隐藏
        $('#togglePassword').addEventListener('click', () => this.togglePasswordVisibility());
        
        // Sheet 过滤规则
        $('#addSheetFilter').addEventListener('click', () => this.addSheetFilter());
        $('#newSheetFilter').addEventListener('keyup', (e) => {
            if (e.key === 'Enter') this.addSheetFilter();
        });
        $('#saveSheetFilter').addEventListener('click', () => this.saveSheetFilters());
        
        // 字段映射
        $('#addFieldMapping').addEventListener('click', () => this.addFieldMapping());
        $('#saveFieldMapping').addEventListener('click', () => this.saveFieldMappings());
        
        // 字段搜索
        $('#fieldSearchInput').addEventListener('input', (e) => {
            this.fieldSearchKeyword = e.target.value.trim().toLowerCase();
            this.renderFieldMappings();
        });
        
        // 配置管理
        $('#downloadConfig').addEventListener('click', () => this.downloadConfig());
        $('#uploadConfig').addEventListener('change', (e) => this.uploadConfig(e));
        
        window.addEventListener('pagechange', (e) => {
            if (e.detail.page === 'settings') {
                this.loadConfig();
            }
        });
    }
    
    togglePasswordVisibility() {
        const input = $('#configPasswd');
        const icon = $('#togglePassword .eye-icon');
        
        if (input.type === 'password') {
            input.type = 'text';
            icon.textContent = '🙈';
        } else {
            input.type = 'password';
            icon.textContent = '👁';
        }
    }
    
    async loadConfig() {
        try {
            const config = await api('/config/full');
            
            // 数据库配置
            $('#configHost').value = config.mysql?.host || '';
            $('#configPort').value = config.mysql?.port || 3306;
            $('#configDbname').value = config.mysql?.dbname || '';
            $('#configUser').value = config.mysql?.user || '';
            $('#configPasswd').value = config.mysql?.passwd || '';
            $('#configUpdate').textContent = `更新时间: ${config.update || '-'}`;
            
            // Sheet 过滤规则
            this.sheetFilters = config.sheet_filter || [];
            this.renderSheetFilters();
            
            // 字段映射
            this.extractFields = config.extract_fields || [];
            this.renderFieldMappings();
            
        } catch (error) {
            showToast(`加载配置失败: ${error.message}`, 'error');
        }
    }
    
    async saveMysqlConfig() {
        const data = {
            host: $('#configHost').value.trim(),
            port: parseInt($('#configPort').value) || 3306,
            user: $('#configUser').value.trim(),
            passwd: $('#configPasswd').value,
            dbname: $('#configDbname').value.trim()
        };
        
        if (!data.host || !data.user || !data.dbname) {
            showToast('请填写完整的数据库配置', 'warning');
            return;
        }
        
        try {
            const result = await api('/config/mysql', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            showToast('数据库配置已保存', 'success');
            $('#configUpdate').textContent = `更新时间: ${result.update}`;
        } catch (error) {
            showToast(`保存失败: ${error.message}`, 'error');
        }
    }
    
    async testConnection() {
        try {
            const result = await api('/database/test', { method: 'POST' });
            if (result.success) {
                showToast('数据库连接成功', 'success');
            } else {
                showToast(`连接失败: ${result.message}`, 'error');
            }
        } catch (error) {
            showToast(`测试失败: ${error.message}`, 'error');
        }
    }
    
    // ==================== Sheet 过滤规则 ====================
    
    renderSheetFilters() {
        const container = $('#sheetFilterList');
        if (this.sheetFilters.length === 0) {
            container.innerHTML = '<div class="empty-hint">暂无过滤规则</div>';
            return;
        }
        
        container.innerHTML = this.sheetFilters.map((filter, index) => `
            <div class="filter-item" data-index="${index}">
                <span class="filter-text">${filter}</span>
                <button class="btn-icon remove-filter" data-index="${index}" title="删除">✕</button>
            </div>
        `).join('');
        
        // 绑定删除事件
        container.querySelectorAll('.remove-filter').forEach(btn => {
            btn.addEventListener('click', () => {
                const index = parseInt(btn.dataset.index);
                this.sheetFilters.splice(index, 1);
                this.renderSheetFilters();
            });
        });
    }
    
    addSheetFilter() {
        const input = $('#newSheetFilter');
        const value = input.value.trim();
        
        if (!value) {
            showToast('请输入过滤关键词', 'warning');
            return;
        }
        
        if (this.sheetFilters.includes(value)) {
            showToast('该关键词已存在', 'warning');
            return;
        }
        
        this.sheetFilters.push(value);
        input.value = '';
        this.renderSheetFilters();
    }
    
    async saveSheetFilters() {
        try {
            const result = await api('/config/sheet-filter', {
                method: 'POST',
                body: JSON.stringify(this.sheetFilters)
            });
            showToast('Sheet 过滤规则已保存', 'success');
            $('#configUpdate').textContent = `更新时间: ${result.update}`;
        } catch (error) {
            showToast(`保存失败: ${error.message}`, 'error');
        }
    }
    
    // ==================== 字段映射配置 ====================
    
    renderFieldMappings() {
        const container = $('#fieldMappingList');
        
        const countEl = $('#fieldCount');
        
        // 更新字段数量显示
        if (countEl) {
            countEl.textContent = `${this.extractFields.length} 个字段`;
        }
        
        if (this.extractFields.length === 0) {
            container.innerHTML = '<div class="empty-hint">暂无字段映射，点击下方按钮添加</div>';
            return;
        }
        
        // 可用的字段类型
        const fieldTypes = [
            { value: 'string', label: '字符串' },
            { value: 'datetime', label: '日期时间' },
            { value: 'int', label: '整数' },
            { value: 'float', label: '浮点数' },
            { value: 'text', label: '长文本' }
        ];
        
        container.innerHTML = this.extractFields.map((field, index) => {
            // 根据搜索关键词决定是否显示
            const shouldShow = !this.fieldSearchKeyword || (() => {
                const fieldName = (field.Field || '').toLowerCase();
                const extractSources = (field.Extract || []).join(' ').toLowerCase();
                return fieldName.includes(this.fieldSearchKeyword) || extractSources.includes(this.fieldSearchKeyword);
            })();
            
            return `
            <div class="field-mapping-item" data-index="${index}" ${!shouldShow ? 'style="display: none;"' : ''}>
                <span class="field-mapping-number">${index + 1}</span>
                <button class="btn-icon remove-mapping" data-index="${index}" title="删除此映射">✕</button>
                <div class="field-mapping-header">
                    <div class="field-name">
                        <label>数据库字段名</label>
                        <input type="text" class="form-input field-input" value="${field.Field || ''}" 
                               data-index="${index}" data-prop="Field" placeholder="输入字段名">
                    </div>
                    <div class="field-type">
                        <label>字段类型</label>
                        <select class="form-select type-select" data-index="${index}">
                            ${fieldTypes.map(t => `
                                <option value="${t.value}" ${(field.Type || 'string') === t.value ? 'selected' : ''}>
                                    ${t.label}
                                </option>
                            `).join('')}
                        </select>
                    </div>
                </div>
                <div class="extract-list">
                    <div class="extract-list-header">
                        <label>提取来源 (${(field.Extract || []).length} 个)</label>
                        <div class="add-extract-row">
                            <input type="text" class="form-input extract-input" placeholder="输入 Excel 列名" 
                                   data-index="${index}">
                            <button class="btn btn-sm btn-outline add-extract" data-index="${index}">添加</button>
                        </div>
                    </div>
                    ${(field.Extract || []).length > 0 ? `
                        <div class="extract-tree" data-index="${index}">
                            ${(field.Extract || []).map((extract, ei) => `
                                <div class="extract-tree-item">
                                    <span class="tree-text">${extract}</span>
                                    <button class="tree-remove" data-field="${index}" data-extract="${ei}" title="删除">✕</button>
                                </div>
                            `).join('')}
                        </div>
                    ` : `
                        <div class="extract-empty">暂无提取来源，请在下方添加</div>
                    `}
                </div>
            </div>
        `;
        }).join('');
        
        // 绑定删除映射事件
        container.querySelectorAll('.remove-mapping').forEach(btn => {
            btn.addEventListener('click', () => {
                const index = parseInt(btn.dataset.index);
                this.extractFields.splice(index, 1);
                this.renderFieldMappings();
            });
        });
        
        // 绑定字段名修改事件
        container.querySelectorAll('.field-input').forEach(input => {
            input.addEventListener('change', () => {
                const index = parseInt(input.dataset.index);
                this.extractFields[index].Field = input.value.trim();
            });
        });
        
        // 绑定字段类型修改事件
        container.querySelectorAll('.type-select').forEach(select => {
            select.addEventListener('change', () => {
                const index = parseInt(select.dataset.index);
                this.extractFields[index].Type = select.value;
            });
        });
        
        // 绑定删除提取来源事件
        container.querySelectorAll('.tree-remove').forEach(btn => {
            btn.addEventListener('click', () => {
                const fieldIndex = parseInt(btn.dataset.field);
                const extractIndex = parseInt(btn.dataset.extract);
                this.extractFields[fieldIndex].Extract.splice(extractIndex, 1);
                this.renderFieldMappings();
            });
        });
        
        // 绑定添加提取来源事件
        container.querySelectorAll('.add-extract').forEach(btn => {
            btn.addEventListener('click', () => {
                const index = parseInt(btn.dataset.index);
                const input = container.querySelector(`.extract-input[data-index="${index}"]`);
                const value = input.value.trim();
                
                if (!value) return;
                
                if (!this.extractFields[index].Extract) {
                    this.extractFields[index].Extract = [];
                }
                
                if (!this.extractFields[index].Extract.includes(value)) {
                    this.extractFields[index].Extract.push(value);
                    this.renderFieldMappings();
                } else {
                    showToast('该来源已存在', 'warning');
                }
            });
        });
        
        // 绑定回车添加
        container.querySelectorAll('.extract-input').forEach(input => {
            input.addEventListener('keyup', (e) => {
                if (e.key === 'Enter') {
                    const index = parseInt(input.dataset.index);
                    container.querySelector(`.add-extract[data-index="${index}"]`).click();
                }
            });
        });
    }
    
    addFieldMapping() {
        this.extractFields.push({
            Field: '',
            Type: 'string',
            Extract: []
        });
        this.renderFieldMappings();
        
        // 滚动到底部
        const container = $('#fieldMappingList');
        container.scrollTop = container.scrollHeight;
    }
    
    async saveFieldMappings() {
        // 过滤空字段
        const validFields = this.extractFields.filter(f => f.Field && f.Field.trim());
        
        if (validFields.length === 0) {
            showToast('请至少添加一个有效的字段映射', 'warning');
            return;
        }
        
        try {
            const result = await api('/config/extract-fields', {
                method: 'POST',
                body: JSON.stringify(validFields)
            });
            this.extractFields = validFields;
            showToast('字段映射配置已保存', 'success');
            $('#configUpdate').textContent = `更新时间: ${result.update}`;
        } catch (error) {
            showToast(`保存失败: ${error.message}`, 'error');
        }
    }
    
    async downloadConfig() {
        try {
            const response = await fetch('/api/config/download', {
                method: 'GET'
            });
            
            if (!response.ok) {
                throw new Error('下载失败');
            }
            
            // 获取文件名（从 Content-Disposition 头或使用默认名称）
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'Configure.json';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }
            
            // 下载文件
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showToast('配置文件下载成功', 'success');
        } catch (error) {
            showToast(`下载失败: ${error.message}`, 'error');
        }
    }
    
    async uploadConfig(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        // 验证文件类型
        if (!file.name.endsWith('.json')) {
            showToast('只支持 JSON 格式的配置文件', 'error');
            event.target.value = '';
            return;
        }
        
        // 确认上传
        const confirmed = await showConfirm(
            '上传配置',
            `确定要上传配置文件 "${file.name}" 吗？当前配置将被替换，系统会自动备份原配置。`
        );
        
        if (!confirmed) {
            event.target.value = '';
            return;
        }
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/api/config/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail || '上传失败');
            }
            
            // 重新加载配置
            await this.loadConfig();
            
            let message = '配置文件上传成功';
            if (result.backup) {
                message += `，原配置已备份为 ${result.backup}`;
            }
            
            showToast(message, 'success');
            $('#configUpdate').textContent = `更新时间: ${result.update}`;
            
        } catch (error) {
            showToast(`上传失败: ${error.message}`, 'error');
        } finally {
            // 清空文件选择，允许重复选择同一文件
            event.target.value = '';
        }
    }
}


// ==================== 初始化 ====================

// ==================== Cache 大小显示 ====================

async function updateCacheSize() {
    const cacheSizeEl = $('#cacheSize');
    if (!cacheSizeEl) return;
    
    try {
        const result = await api('/cache/size');
        if (result.success) {
            cacheSizeEl.textContent = `历史数据: ${result.size_formatted}`;
        } else {
            cacheSizeEl.textContent = '计算失败';
        }
    } catch (error) {
        cacheSizeEl.textContent = '计算失败';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // 主题管理（最先初始化）
    new ThemeManager();
    
    // 其他模块
    const navigation = new Navigation();
    window.fileUploader = new FileUploader();
    new HistoryManager();
    new DatabaseManager();
    new SettingsManager();
    
    // 恢复上次访问的页面
    navigation.restorePage();
    
    // 历史数据大小已在处理历史页面显示，不再在侧边栏显示
    
    console.log('CapacityReport v2.0.0 已加载');
    
    // 重启服务按钮事件（使用事件委托，支持所有页面的重启按钮）
    document.addEventListener('click', async (e) => {
        if (e.target.closest('.restart-btn') || e.target.closest('#restartService')) {
            e.preventDefault();
            e.stopPropagation();
            
            const confirmed = await showConfirm(
                '重启服务',
                '确定要重启服务吗？这将中断当前所有操作。'
            );
            
            if (!confirmed) return;
            
            // 显示加载遮罩
            showRestartOverlay('正在重启服务...');
            
            try {
                await api('/service/restart', { method: 'POST' });
            } catch (error) {
                // 请求可能因为服务重启而失败，这是正常的
            }
            
            // 开始轮询检测服务是否恢复
            pollServiceStatus();
        }
    });
    
    // 显示重启加载遮罩
    function showRestartOverlay(message) {
        let overlay = $('#restartOverlay');
        if (overlay) {
            overlay.querySelector('.restart-overlay-text').textContent = message;
            overlay.classList.add('active');
        }
    }
    
    // 隐藏重启加载遮罩
    function hideRestartOverlay() {
        let overlay = $('#restartOverlay');
        if (overlay) {
            overlay.classList.remove('active');
        }
    }
    
    // 更新遮罩文字
    function updateRestartOverlayText(message) {
        let overlay = $('#restartOverlay');
        if (overlay) {
            overlay.querySelector('.restart-overlay-text').textContent = message;
        }
    }
    
    // 轮询检测服务状态
    function pollServiceStatus() {
        let attempts = 0;
        const maxAttempts = 60; // 最多尝试 60 次（约 5 分钟）
        const pollInterval = 5000; // 每 5 秒检测一次
        
        const checkService = async () => {
            attempts++;
            
            try {
                const response = await fetch('/api/service/status', {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (response.ok) {
                    // 服务已恢复
                    updateRestartOverlayText('服务已恢复，正在刷新页面...');
                    setTimeout(() => {
                        window.location.reload();
                    }, 500);
                    return;
                }
            } catch (error) {
                // 服务还未恢复，继续轮询
            }
            
            if (attempts < maxAttempts) {
                setTimeout(checkService, pollInterval);
            } else {
                // 超时，提示用户手动刷新
                hideRestartOverlay();
                showToast('服务重启超时，请手动刷新页面', 'warning');
            }
        };
        
        // 延迟 3 秒后开始轮询，给服务一些启动时间
        setTimeout(checkService, 3000);
    }
    
    // 侧边栏折叠功能
    const sidebar = $('#sidebar');
    
    // 从 localStorage 读取折叠状态
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (isCollapsed && sidebar) {
        sidebar.classList.add('collapsed');
    }
    
    // 使用事件委托为所有侧边栏切换按钮绑定事件
    document.addEventListener('click', (e) => {
        if (e.target.closest('#sidebarToggle') || e.target.closest('.sidebar-toggle')) {
            e.preventDefault();
            e.stopPropagation();
            if (sidebar) {
                sidebar.classList.toggle('collapsed');
                const collapsed = sidebar.classList.contains('collapsed');
                localStorage.setItem('sidebarCollapsed', collapsed ? 'true' : 'false');
            }
        }
    });
    
    // 初始化脚本编辑器（延迟初始化，只在页面显示时创建）
    window.scriptEditor = new ScriptEditor();
    
    // 监听页面切换事件，延迟初始化 Monaco Editor
    window.addEventListener('pagechange', (e) => {
        if (e.detail.page === 'script' && window.scriptEditor) {
            // 延迟一点确保 DOM 已更新
            setTimeout(() => {
                window.scriptEditor.ensureEditor();
            }, 100);
        }
    });
    
    // 如果初始页面就是脚本编辑页面，也需要初始化
    const initialPage = document.querySelector('.page.active')?.id;
    if (initialPage === 'page-script' && window.scriptEditor) {
        setTimeout(() => {
            window.scriptEditor.ensureEditor();
        }, 300);
    }
});


// ==================== 脚本编辑器类 ====================

class ScriptEditor {
    constructor() {
        this.editor = null;
        this.originalContent = '';
        this.isModified = false;
        this.monacoReady = false;
        this.monacoLoading = false;
        this.initAttempted = false;
        
        // 只绑定事件，不立即初始化编辑器
        this.bindEvents();
    }
    
    async waitForLoader() {
        // 等待 loader.js 加载完成
        let attempts = 0;
        const maxAttempts = 50; // 最多等待 5 秒
        
        while (attempts < maxAttempts) {
            if (typeof require !== 'undefined' && typeof require.config === 'function') {
                return true;
            }
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }
        
        return false;
    }
    
    async initMonaco() {
        // 如果正在加载或已加载，直接返回
        if (this.monacoLoading || this.monacoReady) {
            return;
        }
        
        this.monacoLoading = true;
        
        try {
            // 等待 loader.js 加载完成
            const loaderReady = await this.waitForLoader();
            if (!loaderReady) {
                throw new Error('Monaco Editor loader.js 加载超时');
            }
            
            // 只在第一次配置，避免重复配置导致冲突
            if (!window.__monacoConfigSet) {
                require.config({
                    paths: {
                        'vs': '/static/lib/monaco/vs'
                    },
                    'vs/nls': {
                        availableLanguages: {
                            '*': 'zh-cn'  // 使用中文语言包
                        }
                    },
                    // 添加错误处理配置
                    onError: (err) => {
                        console.error('Monaco Editor 模块加载错误:', err);
                        // 不抛出错误，让加载继续
                    }
                });
                window.__monacoConfigSet = true;
            }
            
            // 先预加载关键依赖模块，确保它们完全加载
            // 这样可以避免竞态条件导致的 undefined 描述符问题
            await new Promise((resolve, reject) => {
                setTimeout(() => {
                    try {
                        // 先加载 editor.api，确保基础 API 可用
                        require(['vs/editor.api.001a2486'], (apiModule) => {
                            if (!apiModule || !apiModule.editor) {
                                reject(new Error('editor.api 模块加载不完整'));
                                return;
                            }
                            // 验证关键 API 是否可用
                            if (!apiModule.editor || typeof apiModule.editor.create !== 'function') {
                                reject(new Error('editor.api 缺少关键方法'));
                                return;
                            }
                            console.log('editor.api 已加载并验证');
                            resolve();
                        }, (err) => {
                            console.error('editor.api 加载失败:', err);
                            reject(err);
                        });
                    } catch (error) {
                        reject(error);
                    }
                }, 100);
            });
            
            // 再等待一点时间，确保所有依赖模块完全初始化
            await new Promise(resolve => setTimeout(resolve, 150));
            
            // 再加载完整的编辑器
            await new Promise((resolve, reject) => {
                try {
                    require(['vs/editor/editor.main'], (module) => {
                        // 检查模块是否正确加载
                        if (!module || !module.m) {
                            reject(new Error('Monaco Editor 模块加载不完整'));
                            return;
                        }
                        
                        // 验证关键 API 是否可用
                        if (!module.m.editor || !module.m.editor.create) {
                            reject(new Error('Monaco Editor API 不完整'));
                            return;
                        }
                        
                        // 将模块暴露到全局
                        window.monaco = module.m;
                        
                        this.monacoReady = true;
                        this.monacoLoading = false;
                        console.log('Monaco Editor 加载成功');
                        resolve();
                    }, (err) => {
                        this.monacoLoading = false;
                        console.error('Monaco Editor 模块加载失败:', err);
                        // 尝试获取更详细的错误信息
                        if (err && err.requireModules) {
                            console.error('失败的模块:', err.requireModules);
                        }
                        reject(err);
                    });
                } catch (error) {
                    this.monacoLoading = false;
                    console.error('Monaco Editor 加载异常:', error);
                    reject(error);
                }
            });
        } catch (error) {
            this.monacoLoading = false;
            console.error('初始化 Monaco Editor 失败:', error);
            showToast('编辑器加载失败: ' + error.message, 'error');
        }
    }
    
    async ensureEditor() {
        // 检查容器是否存在且可见
        const container = document.getElementById('scriptEditor');
        if (!container) {
            console.warn('脚本编辑器容器不存在');
            return;
        }
        
        // 检查容器是否可见
        const page = document.getElementById('page-script');
        if (!page || !page.classList.contains('active')) {
            console.warn('脚本编辑页面未激活');
            return;
        }
        
        // 如果编辑器已创建，只需重新布局
        if (this.editor) {
            setTimeout(() => {
                this.editor.layout();
            }, 100);
            return;
        }
        
        // 如果 Monaco 未加载，先加载
        if (!this.monacoReady) {
            await this.initMonaco();
        }
        
        // 创建编辑器
        if (this.monacoReady && !this.editor) {
            this.createEditor();
        }
    }
    
    createEditor() {
        const container = document.getElementById('scriptEditor');
        if (!container) {
            console.error('脚本编辑器容器不存在');
            return;
        }
        
        // 如果编辑器已存在，先销毁
        if (this.editor) {
            try {
                this.editor.dispose();
            } catch (e) {
                console.warn('销毁旧编辑器失败:', e);
            }
        }
        
        try {
            // 检测当前主题
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            
            // 创建编辑器实例
            this.editor = monaco.editor.create(container, {
            value: '-- 加载中...',
            language: 'sql',
            theme: isDark ? 'vs-dark' : 'vs',
            fontSize: 14,
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', monospace",
            minimap: { enabled: true },
            automaticLayout: true,
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            lineNumbers: 'on',
            renderLineHighlight: 'all',
            selectOnLineNumbers: true,
            roundedSelection: true,
            cursorBlinking: 'smooth',
            cursorSmoothCaretAnimation: 'on',
            smoothScrolling: true,
            tabSize: 4,
            insertSpaces: true,
            folding: true,
            foldingStrategy: 'indentation',
            showFoldingControls: 'always',
            bracketPairColorization: { enabled: true },
            guides: {
                bracketPairs: true,
                indentation: true
            },
            suggest: {
                showKeywords: true,
                showSnippets: true
            }
        });
        
        // 监听内容变化
        this.editor.onDidChangeModelContent(() => {
            this.checkModified();
        });
        
        // 监听光标位置变化
        this.editor.onDidChangeCursorPosition((e) => {
            this.updateCursorPosition(e.position);
        });
        
        // 添加快捷键
        this.editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
            this.saveScript();
        });
        
        // 监听窗口大小变化，自动调整布局
        window.addEventListener('resize', () => {
            if (this.editor) {
                this.editor.layout();
            }
        });
        
        // 延迟加载脚本内容，确保编辑器已完全渲染
        setTimeout(() => {
            this.loadScript();
        }, 200);
        } catch (error) {
            console.error('创建编辑器失败:', error);
            showToast('创建编辑器失败: ' + error.message, 'error');
        }
    }
    
    async loadScript() {
        try {
            this.updateStatus('加载中...');
            const result = await api('/script/content');
            
            if (result.success) {
                this.originalContent = result.content;
                if (this.editor) {
                    this.editor.setValue(result.content);
                }
                
                // 更新路径和修改时间
                const pathEl = document.getElementById('scriptPath');
                const modifiedEl = document.getElementById('scriptModified');
                
                if (pathEl) {
                    pathEl.textContent = result.path;
                    pathEl.title = result.path;
                }
                
                if (modifiedEl && result.modified) {
                    modifiedEl.textContent = `最后修改: ${result.modified}`;
                }
                
                this.isModified = false;
                this.updateStatus('就绪');
            } else {
                showToast('加载脚本失败: ' + result.error, 'error');
                this.updateStatus('加载失败');
            }
        } catch (error) {
            showToast('加载脚本失败: ' + error.message, 'error');
            this.updateStatus('加载失败');
        }
    }
    
    async saveScript() {
        if (!this.editor) return;
        
        try {
            this.updateStatus('保存中...');
            const content = this.editor.getValue();
            
            const result = await api('/script/save', {
                method: 'POST',
                body: JSON.stringify({ content })
            });
            
            if (result.success) {
                this.originalContent = content;
                this.isModified = false;
                
                // 更新修改时间
                const modifiedEl = document.getElementById('scriptModified');
                if (modifiedEl && result.modified) {
                    modifiedEl.textContent = `最后修改: ${result.modified}`;
                }
                
                showToast('脚本保存成功', 'success');
                this.updateStatus('已保存');
            } else {
                showToast('保存失败: ' + result.error, 'error');
                this.updateStatus('保存失败');
            }
        } catch (error) {
            showToast('保存失败: ' + error.message, 'error');
            this.updateStatus('保存失败');
        }
    }
    
    formatScript() {
        if (!this.editor) return;
        
        // Monaco 内置的格式化功能
        this.editor.getAction('editor.action.formatDocument').run();
        showToast('格式化完成', 'success');
    }
    
    checkModified() {
        if (!this.editor) return;
        
        const current = this.editor.getValue();
        this.isModified = current !== this.originalContent;
        
        // 更新标题显示修改状态
        const saveBtn = document.getElementById('saveScript');
        if (saveBtn) {
            if (this.isModified) {
                saveBtn.classList.add('modified');
                saveBtn.innerHTML = '💾 保存 *';
            } else {
                saveBtn.classList.remove('modified');
                saveBtn.innerHTML = '💾 保存';
            }
        }
    }
    
    updateCursorPosition(position) {
        const cursorEl = document.getElementById('editorCursor');
        if (cursorEl) {
            cursorEl.textContent = `行 ${position.lineNumber}, 列 ${position.column}`;
        }
    }
    
    updateStatus(status) {
        const statusEl = document.getElementById('editorStatus');
        if (statusEl) {
            statusEl.textContent = status;
        }
    }
    
    updateTheme(isDark) {
        if (this.editor) {
            monaco.editor.setTheme(isDark ? 'vs-dark' : 'vs');
        }
    }
    
    bindEvents() {
        // 保存按钮
        document.addEventListener('click', (e) => {
            if (e.target.closest('#saveScript')) {
                this.saveScript();
            }
            if (e.target.closest('#formatScript')) {
                this.formatScript();
            }
        });
        
        // 监听主题变化
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-theme') {
                    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                    this.updateTheme(isDark);
                }
            });
        });
        
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-theme']
        });
        
        // 页面离开前提示保存
        window.addEventListener('beforeunload', (e) => {
            if (this.isModified) {
                e.preventDefault();
                e.returnValue = '您有未保存的更改，确定要离开吗？';
                return e.returnValue;
            }
        });
    }
}
