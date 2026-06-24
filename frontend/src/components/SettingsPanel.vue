<template>
  <div class="settings-workspace">
    <input ref="configInput" class="hidden-input" type="file" accept=".json" @change="uploadConfigFile" />

    <n-card size="small" class="work-card settings-tabs-card">
      <n-tabs type="line" animated class="settings-tabs">
        <n-tab-pane name="backend" tab="数据源 / 仓库">
          <div class="settings-database-panel">
            <div class="settings-database-stack">
              <n-card title="后端类型" size="small" class="work-card">
                <n-form label-placement="top">
                  <n-form-item label="数据源">
                    <n-radio-group v-model:value="sourceType">
                      <n-radio-button value="sftp">SFTP</n-radio-button>
                      <n-radio-button value="ftp">FTP</n-radio-button>
                      <n-radio-button value="metrix">Metrix 存储平台</n-radio-button>
                    </n-radio-group>
                  </n-form-item>
                  <n-form-item label="数据仓库">
                    <n-radio-group v-model:value="warehouseType">
                      <n-radio-button value="mysql">MySQL</n-radio-button>
                      <n-radio-button value="metrix">Metrix 数据库平台</n-radio-button>
                    </n-radio-group>
                  </n-form-item>
                  <p class="form-hint">两侧可独立选择：源用 FTP/SFTP 或 Metrix 存储平台；仓库用本地 MySQL 或 Metrix 数据库平台。选 Metrix 时在下方填写连接；选 FTP/SFTP 或 MySQL 时在对应标签页填写。源目录在「远程数据源」标签页的「远程目录」。</p>
                </n-form>
                <template #footer>
                  <n-space justify="end">
                    <n-button type="primary" :loading="savingBackend" @click="saveBackend">保存类型</n-button>
                  </n-space>
                </template>
              </n-card>

              <n-card title="Metrix 连接（存储平台 / 数据库平台）" size="small" class="work-card">
                <n-form label-placement="top">
                  <n-form-item label="平台地址 (api_base)">
                    <n-input v-model:value="metrixForm.base_url" placeholder="http://host.docker.internal:8000" />
                  </n-form-item>
                  <n-form-item label="API Token">
                    <n-input v-model:value="metrixForm.token" type="password" show-password-on="click" placeholder="mtx_..." />
                  </n-form-item>
                  <n-grid :cols="12" :x-gap="12">
                    <n-gi :span="6">
                      <n-form-item label="储存连接 ID">
                        <n-input v-model:value="metrixForm.storage_id" placeholder="stg_..." />
                      </n-form-item>
                    </n-gi>
                    <n-gi :span="6">
                      <n-form-item label="数据库连接 ID">
                        <n-input v-model:value="metrixForm.database_conn_id" placeholder="db_..." />
                      </n-form-item>
                    </n-gi>
                  </n-grid>
                  <n-grid :cols="12" :x-gap="12">
                    <n-gi :span="8">
                      <n-form-item label="目标库/Schema">
                        <n-input v-model:value="metrixForm.target_database" placeholder="连接已指定库时可空" />
                      </n-form-item>
                    </n-gi>
                    <n-gi :span="4">
                      <n-form-item label="最近 N 天回退">
                        <n-input-number v-model:value="metrixForm.recent_days" class="full-width" :min="1" :precision="0" />
                      </n-form-item>
                    </n-gi>
                  </n-grid>
                  <p class="form-hint">仅当数据源或仓库选择 Metrix 时使用。存储平台用 storage_id，数据库平台用 database_conn_id，二者共用地址与 Token。</p>
                </n-form>
                <template #footer>
                  <n-space justify="end">
                    <n-button type="primary" :loading="savingMetrix" @click="saveMetrix">保存连接</n-button>
                    <n-button :loading="testingRemote" @click="testRemote">测试储存</n-button>
                  </n-space>
                </template>
              </n-card>
            </div>
          </div>
        </n-tab-pane>

        <n-tab-pane name="database" tab="数据库">
          <div class="settings-database-panel">
            <div class="settings-database-stack">
              <n-card title="MySQL配置" size="small" class="work-card">
                <n-form label-placement="top">
                  <n-grid :cols="12" :x-gap="12">
                    <n-gi :span="8">
                      <n-form-item label="主机地址">
                        <n-input v-model:value="mysqlForm.host" placeholder="localhost" />
                      </n-form-item>
                    </n-gi>
                    <n-gi :span="4">
                      <n-form-item label="端口">
                        <n-input-number v-model:value="mysqlForm.port" class="full-width" :min="1" :max="65535" />
                      </n-form-item>
                    </n-gi>
                  </n-grid>
                  <n-form-item label="数据库名">
                    <n-input v-model:value="mysqlForm.dbname" placeholder="CapacityReport" />
                  </n-form-item>
                  <n-grid :cols="12" :x-gap="12">
                    <n-gi :span="6">
                      <n-form-item label="用户名">
                        <n-input v-model:value="mysqlForm.user" placeholder="root" />
                      </n-form-item>
                    </n-gi>
                    <n-gi :span="6">
                      <n-form-item label="密码">
                        <n-input v-model:value="mysqlForm.passwd" type="password" show-password-on="click" />
                      </n-form-item>
                    </n-gi>
                  </n-grid>
                </n-form>

                <template #footer>
                  <n-space justify="end">
                    <n-button type="primary" :loading="savingMysql" @click="saveMysql">保存配置</n-button>
                    <n-button :loading="testingDb" @click="testDatabase">测试连接</n-button>
                  </n-space>
                </template>
              </n-card>

              <n-card title="处理历史保留" size="small" class="work-card work-card-narrow">
                <n-form label-placement="top">
                  <n-grid :cols="12" :x-gap="12">
                    <n-gi :span="6">
                      <n-form-item label="自动清理处理历史">
                        <n-switch v-model:value="historyRetentionForm.enabled" />
                      </n-form-item>
                    </n-gi>
                    <n-gi :span="6">
                      <n-form-item label="保留最近次数">
                        <n-input-number
                          v-model:value="historyRetentionForm.keep_count"
                          class="full-width"
                          :min="0"
                          :precision="0"
                          :disabled="!historyRetentionForm.enabled"
                        />
                      </n-form-item>
                    </n-gi>
                  </n-grid>
                  <p class="form-hint">关闭后不自动删除处理历史；启用后会在任务结束时自动清理，设置为 0 表示不保留历史，否则只保留最近指定次数的处理历史。</p>
                </n-form>

                <template #footer>
                  <n-space justify="end">
                    <n-button type="primary" :loading="savingHistoryRetention" @click="saveHistoryRetention">
                      保存配置
                    </n-button>
                  </n-space>
                </template>
              </n-card>
            </div>
          </div>
        </n-tab-pane>

        <n-tab-pane name="remote" tab="远程数据源">
          <div class="settings-remote-panel">
            <n-card title="数据推送信息" size="small" class="work-card settings-remote-card">
              <n-form label-placement="top">
                <div class="remote-connection-row">
                  <n-form-item label="协议">
                    <n-select
                      v-model:value="remoteForm.protocol"
                      :options="remoteProtocolOptions"
                      @update:value="updateRemoteProtocol"
                    />
                  </n-form-item>
                  <n-form-item label="服务器地址">
                    <n-input v-model:value="remoteForm.host" placeholder="192.168.1.10" />
                  </n-form-item>
                  <n-form-item label="端口">
                    <n-input-number v-model:value="remoteForm.port" class="full-width" :min="1" :max="65535" />
                  </n-form-item>
                  <n-form-item label="超时秒数">
                    <n-input-number v-model:value="remoteForm.timeout" class="full-width" :min="1" :max="600" />
                  </n-form-item>
                  <n-form-item label="FTP 被动模式" class="remote-passive-field">
                    <n-switch v-model:value="remoteForm.passive" :disabled="remoteForm.protocol !== 'ftp'" />
                  </n-form-item>
                </div>
                <n-grid :cols="12" :x-gap="12">
                  <n-gi :span="6">
                    <n-form-item label="用户名">
                      <n-input v-model:value="remoteForm.user" placeholder="remote user" />
                    </n-form-item>
                  </n-gi>
                  <n-gi :span="6">
                    <n-form-item label="密码">
                      <n-input v-model:value="remoteForm.passwd" type="password" show-password-on="click" />
                    </n-form-item>
                  </n-gi>
                </n-grid>
                <n-form-item label="远程目录">
                  <n-input v-model:value="remoteForm.remote_dir" placeholder="/CapacityReportData" />
                </n-form-item>
                <div class="remote-toggle-row">
                  <n-form-item label="启用远程自动化">
                    <n-switch v-model:value="remoteForm.enabled" />
                  </n-form-item>
                  <n-form-item label="处理成功后删除源文件">
                    <n-switch
                      v-model:value="remoteForm.auto_delete_source"
                      :disabled="remoteForm.auto_scheduler.enabled"
                    />
                  </n-form-item>
                </div>
                <p class="form-hint">自动化执行会递归下载该目录下的全部文件和文件夹到本地缓存，再按现有处理流程入库和执行脚本；自动删除源文件只会在处理成功后删除远程文件，保留目录结构。</p>
              </n-form>

              <template #footer>
                <n-space justify="end">
                  <n-button type="primary" :loading="savingRemote" @click="saveRemote">保存配置</n-button>
                  <n-button :loading="testingRemote" @click="testRemote">测试连接</n-button>
                </n-space>
              </template>
            </n-card>
          </div>
        </n-tab-pane>

        <n-tab-pane name="scheduler" tab="自动调度">
          <div class="settings-scheduler-panel">
            <n-card title="自动调度" size="small" class="work-card settings-scheduler-card">
              <n-form label-placement="top">
                <n-grid :cols="12" :x-gap="12">
                  <n-gi :span="4">
                    <n-form-item label="启用自动调度">
                      <n-switch v-model:value="remoteForm.auto_scheduler.enabled" :disabled="!remoteForm.enabled" />
                    </n-form-item>
                  </n-gi>
                  <n-gi :span="4">
                    <n-form-item label="检查间隔（小时）">
                      <n-input-number
                        v-model:value="remoteForm.auto_scheduler.check_interval_hours"
                        class="full-width"
                        :min="1"
                        :precision="0"
                        :disabled="schedulerControlsDisabled"
                      />
                    </n-form-item>
                  </n-gi>
                  <n-gi :span="4">
                    <n-form-item label="目标周期">
                      <n-select
                        v-model:value="remoteForm.auto_scheduler.week_offset"
                        :options="schedulerWeekOptions"
                        :disabled="schedulerControlsDisabled"
                      />
                    </n-form-item>
                  </n-gi>
                </n-grid>
                <n-form-item label="预期目录">
                  <div class="scheduler-dir-editor">
                    <n-input-group>
                      <n-input
                        v-model:value="newSchedulerDirectory"
                        placeholder="例如 4G/FDD"
                        :disabled="schedulerControlsDisabled"
                        @keydown.enter.prevent="addSchedulerDirectory"
                      />
                      <n-button :disabled="schedulerControlsDisabled" @click="addSchedulerDirectory">
                        添加
                      </n-button>
                    </n-input-group>
                    <div class="scheduler-dir-tags">
                      <n-tag
                        v-for="(directory, index) in remoteForm.auto_scheduler.expected_directories"
                        :key="`${directory}-${index}`"
                        closable
                        :disabled="schedulerControlsDisabled"
                        @close="removeSchedulerDirectory(index)"
                      >
                        {{ directory }}
                      </n-tag>
                      <n-tag v-if="remoteForm.auto_scheduler.expected_directories.length === 0" type="default">
                        按实际 ZIP 目录检测
                      </n-tag>
                    </div>
                  </div>
                </n-form-item>
                <p class="form-hint">自动调度依赖远程自动化；关闭远程自动化时会自动关闭调度。启用调度后会按文件名日期检查目标自然周 7 天，并强制开启处理成功后删除源文件。</p>
              </n-form>

              <div class="scheduler-status-panel">
                <div class="scheduler-status-header">
                  <span>调度状态</span>
                  <n-tag size="small" :type="schedulerStatusTagType">
                    {{ schedulerStatusLabel }}
                  </n-tag>
                </div>
                <div class="scheduler-status-grid">
                  <div>
                    <span>目标周</span>
                    <strong>{{ schedulerTargetWeekText }}</strong>
                  </div>
                  <div>
                    <span>下次检查</span>
                    <strong>{{ schedulerStatus?.next_check_at || '-' }}</strong>
                  </div>
                  <div>
                    <span>就绪标识</span>
                    <strong>{{ schedulerStatus?.ready_flag?.exists ? '已存在' : '无' }}</strong>
                  </div>
                </div>
                <p class="form-hint">{{ schedulerStatus?.last_message || '自动调度状态尚未加载' }}</p>
                <div v-if="schedulerDirectoryRows.length > 0" class="scheduler-directory-list">
                  <div v-for="row in schedulerDirectoryRows" :key="row.name" class="scheduler-directory-row">
                    <span class="scheduler-directory-name">{{ row.displayName }}</span>
                    <n-tag size="small" :type="row.skipped ? 'info' : row.ready ? 'success' : 'warning'">
                      {{ row.skipped ? '已停推' : row.ready ? '就绪' : `缺 ${row.missing_days.length} 天` }}
                    </n-tag>
                  </div>
                </div>
                <n-space justify="end" size="small">
                  <n-button size="small" :loading="loadingSchedulerStatus" @click="loadSchedulerStatus">
                    刷新状态
                  </n-button>
                  <n-button
                    size="small"
                    type="primary"
                    :loading="triggeringScheduler"
                    :disabled="!remoteForm.enabled || !remoteForm.auto_scheduler.enabled"
                    @click="triggerSchedulerCheck"
                  >
                    立即检查
                  </n-button>
                </n-space>
              </div>

              <template #footer>
                <n-space justify="end">
                  <n-button type="primary" :loading="savingRemote" @click="saveRemote">保存调度</n-button>
                </n-space>
              </template>
            </n-card>
          </div>
        </n-tab-pane>

        <n-tab-pane name="rules" tab="规则映射">
          <div class="settings-rules-grid">
            <div class="settings-rules-side">
              <n-card title="数据目录映射" size="small" class="work-card">
                <n-space vertical>
                  <p class="form-hint">每行配置一个源目录到暂存表的映射。就绪规则选择“每日7天”时按目标周 7 天检查；选择“自动日/周”时按目录最新文件自动识别日粒度或周粒度。</p>
                  <div class="directory-mapping-list">
                    <div
                      v-for="(item, index) in dataMappingsForm.directories"
                      :key="`${item.path}-${item.table}-${item.ready_rule}-${index}`"
                      class="directory-mapping-row"
                    >
                      <n-input v-model:value="item.path" size="small" placeholder="目录，例如 4G 或 RJ/700M/700RJYD" />
                      <n-input v-model:value="item.table" size="small" placeholder="暂存表，例如 4G_UD" />
                      <n-select v-model:value="item.ready_rule" size="small" :options="readyRuleOptions" />
                      <n-button quaternary circle size="small" type="error" @click="removeDirectoryMapping(index)">
                        <template #icon>
                          <n-icon><CloseOutline /></n-icon>
                        </template>
                      </n-button>
                    </div>
                    <n-empty v-if="dataMappingsForm.directories.length === 0" size="small" description="暂无目录映射" />
                  </div>
                  <n-input-group>
                    <n-input v-model:value="newDirectoryMapping.path" placeholder="目录路径" @keydown.enter.prevent="addDirectoryMapping" />
                    <n-input v-model:value="newDirectoryMapping.table" placeholder="暂存表名" @keydown.enter.prevent="addDirectoryMapping" />
                    <n-select v-model:value="newDirectoryMapping.ready_rule" class="directory-ready-select" :options="readyRuleOptions" />
                    <n-button @click="addDirectoryMapping">添加</n-button>
                  </n-input-group>
                </n-space>

                <template #footer>
                  <n-space justify="end">
                    <n-button type="primary" :loading="savingDirectoryMappings" @click="saveDirectoryMappings">保存目录映射</n-button>
                  </n-space>
                </template>
              </n-card>

              <n-card title="Sheet 过滤规则" size="small" class="work-card">
                <n-space vertical>
                  <p class="form-hint">匹配这些关键词的 Sheet 将被跳过处理</p>
                  <div class="filter-tags">
                    <n-tag
                      v-for="(filter, index) in sheetFilters"
                      :key="`${filter}-${index}`"
                      closable
                      @close="removeSheetFilter(index)"
                    >
                      {{ filter }}
                    </n-tag>
                    <n-empty v-if="sheetFilters.length === 0" size="small" description="暂无过滤规则" />
                  </div>
                  <n-input-group>
                    <n-input
                      v-model:value="newSheetFilter"
                      placeholder="输入需要跳过的 Sheet 关键词"
                      @keydown.enter.prevent="addSheetFilter"
                    />
                    <n-button @click="addSheetFilter">添加</n-button>
                  </n-input-group>
                </n-space>

                <template #footer>
                  <n-space justify="end">
                    <n-button type="primary" :loading="savingSheetFilter" @click="saveSheetFilter">保存规则</n-button>
                  </n-space>
                </template>
              </n-card>
            </div>

            <n-card size="small" class="work-card field-mapping-card">
              <template #header>
                <div class="field-card-header">
                  <div class="field-card-title-row">
                    <div class="field-card-title">
                      <span>字段映射配置</span>
                      <n-tag size="small" round>{{ extractFields.length }} 个字段</n-tag>
                    </div>
                    <n-input
                      v-model:value="fieldSearch"
                      size="small"
                      clearable
                      class="field-search"
                      placeholder="搜索字段..."
                    />
                  </div>
                  <p class="form-hint">定义 Excel 列名到数据库字段的映射规则，提取来源匹配任意一个即可</p>
                </div>
              </template>

              <div class="field-mapping-scroll">
                <n-empty v-if="visibleFieldMappings.length === 0" description="没有匹配的字段配置" />

                <div
                  v-for="{ field, index } in visibleFieldMappings"
                  :key="index"
                  class="field-mapping-item"
                >
                  <div class="field-mapping-number">{{ index + 1 }}</div>
                  <n-button
                    quaternary
                    circle
                    size="small"
                    type="error"
                    class="field-remove-button"
                    @click="removeFieldMapping(index)"
                  >
                    <template #icon>
                      <n-icon><CloseOutline /></n-icon>
                    </template>
                  </n-button>

                  <div class="field-mapping-header">
                    <n-form-item label="数据库字段名" class="field-name-control">
                      <n-input v-model:value="field.Field" placeholder="输入字段名" />
                    </n-form-item>
                    <n-form-item label="字段类型" class="field-type-control">
                      <n-select v-model:value="field.Type" :options="fieldTypeOptions" />
                    </n-form-item>
                  </div>

                  <div class="extract-list">
                    <div class="extract-list-header">
                      <span>提取来源（{{ field.Extract.length }} 个）</span>
                      <n-input-group class="extract-add-group">
                        <n-input
                          v-model:value="newExtractValues[index]"
                          size="small"
                          placeholder="输入 Excel 列名"
                          @keydown.enter.prevent="addExtract(index)"
                        />
                        <n-button size="small" @click="addExtract(index)">添加</n-button>
                      </n-input-group>
                    </div>

                    <div v-if="field.Extract.length > 0" class="extract-tree">
                      <div v-for="(source, sourceIndex) in field.Extract" :key="`${source}-${sourceIndex}`" class="extract-tree-item">
                        <span class="tree-text">{{ source }}</span>
                        <n-button text size="tiny" type="warning" @click="removeExtract(index, sourceIndex)">删除</n-button>
                      </div>
                    </div>
                    <div v-else class="extract-empty">暂无提取来源</div>
                  </div>
                </div>
              </div>

              <template #footer>
                <n-space justify="end">
                  <n-button @click="addFieldMapping">添加字段</n-button>
                  <n-button type="primary" :loading="savingExtractFields" @click="saveExtractFields">
                    保存映射
                  </n-button>
                </n-space>
              </template>
            </n-card>
          </div>
        </n-tab-pane>

        <n-tab-pane name="security" tab="修改密码">
          <div class="settings-security-panel">
            <n-card title="修改登录密码" size="small" class="work-card">
              <n-form label-placement="top">
                <n-form-item label="当前密码">
                  <n-input v-model:value="passwordForm.current_password" type="password" show-password-on="click" />
                </n-form-item>
                <n-form-item label="新密码">
                  <n-input v-model:value="passwordForm.new_password" type="password" show-password-on="click" />
                </n-form-item>
                <n-form-item label="确认新密码">
                  <n-input v-model:value="passwordForm.confirm_password" type="password" show-password-on="click" />
                </n-form-item>
              </n-form>

              <template #footer>
                <n-space justify="end">
                  <n-button type="primary" :loading="changingPassword" @click="changePassword">修改密码</n-button>
                </n-space>
              </template>
            </n-card>
          </div>
        </n-tab-pane>

      </n-tabs>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useDialog, useMessage, type SelectOption } from 'naive-ui';
import { CloseOutline, CloudDownloadOutline, CloudUploadOutline } from '@vicons/ionicons5';

import { apiGet, apiPost, downloadGet, upload } from '../api/client';
import type {
  ApiMessage,
  AppConfig,
  DataDirectoryMapping,
  DataMappingsConfig,
  HistoryRetentionConfig,
  MetrixConfig,
  RemoteAutoSchedulerConfig,
  RemoteDataConfig,
  RemoteSchedulerStatus
} from '../types';
import { showDownloadCompleteDialog } from '../composables/downloadFeedback';
import { resetPageHeader, setPageHeader } from '../composables/pageHeader';

interface ExtractFieldConfig {
  Field: string;
  Type: string;
  Extract: string[];
  [key: string]: unknown;
}

const message = useMessage();
const dialog = useDialog();
const configInput = ref<HTMLInputElement | null>(null);
const configUpdate = ref('');
const configUpdateText = computed(() => `更新时间：${configUpdate.value || '-'}`);
const loading = ref(false);
const testingDb = ref(false);
const testingRemote = ref(false);
const loadingSchedulerStatus = ref(false);
const triggeringScheduler = ref(false);
const savingMysql = ref(false);
const savingRemote = ref(false);
const savingBackend = ref(false);
const savingMetrix = ref(false);
const sourceType = ref<'ftp' | 'sftp' | 'metrix'>('sftp');
const warehouseType = ref<'mysql' | 'metrix'>('mysql');
const savingDirectoryMappings = ref(false);
const savingHistoryRetention = ref(false);
const savingSheetFilter = ref(false);
const savingExtractFields = ref(false);
const changingPassword = ref(false);
const sheetFilters = ref<string[]>([]);
const newSheetFilter = ref('');
const extractFields = ref<ExtractFieldConfig[]>([]);
const fieldSearch = ref('');
const newSchedulerDirectory = ref('');
const schedulerStatus = ref<RemoteSchedulerStatus | null>(null);
const newExtractValues = reactive<Record<number, string>>({});

const mysqlForm = reactive({
  host: '',
  port: 3306 as number | null,
  user: '',
  passwd: '',
  dbname: ''
});

const remoteForm = reactive<RemoteDataConfig>({
  enabled: false,
  protocol: 'sftp',
  host: '',
  port: 22,
  user: '',
  passwd: '',
  remote_dir: '/',
  passive: true,
  timeout: 30,
  auto_delete_source: false,
  auto_scheduler: {
    enabled: false,
    check_interval_hours: 1,
    expected_directories: [],
    week_offset: 0
  }
});

const metrixForm = reactive<MetrixConfig>({
  base_url: 'http://host.docker.internal:8000',
  token: '',
  storage_id: '',
  database_conn_id: '',
  target_database: '',
  recent_days: 7
});

const dataMappingsForm = reactive<DataMappingsConfig>({
  directories: [
    { path: '4G', table: '4G_UD', ready_rule: 'daily' },
    { path: '5G', table: '5G_UD', ready_rule: 'daily' }
  ],
  table_field_mappings: {}
});

const newDirectoryMapping = reactive<DataDirectoryMapping>({
  path: '',
  table: '',
  ready_rule: 'daily'
});

const historyRetentionForm = reactive<HistoryRetentionConfig>({
  enabled: false,
  keep_count: 20
});

const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: ''
});

const fieldTypeOptions: SelectOption[] = [
  { label: '字符串', value: 'string' },
  { label: '整数', value: 'int' },
  { label: '小数', value: 'float' },
  { label: '日期时间', value: 'datetime' }
];
const remoteProtocolOptions: SelectOption[] = [
  { label: 'SFTP', value: 'sftp' },
  { label: 'FTP', value: 'ftp' }
];
const schedulerWeekOptions: SelectOption[] = [
  { label: '上周', value: 0 },
  { label: '上上周', value: -1 }
];
const readyRuleOptions: SelectOption[] = [
  { label: '每日7天', value: 'daily' },
  { label: '自动日/周', value: 'auto' }
];

const visibleFieldMappings = computed(() => {
  const keyword = fieldSearch.value.trim().toLowerCase();
  return extractFields.value
    .map((field, index) => ({ field, index }))
    .filter(({ field }) => {
      if (!keyword) return true;
      const fieldName = field.Field.toLowerCase();
      const extractText = field.Extract.join(' ').toLowerCase();
      return fieldName.includes(keyword) || extractText.includes(keyword);
    });
});
const schedulerStatusLabel = computed(() => {
  if (!schedulerStatus.value) return '未加载';
  if (!schedulerStatus.value.enabled) return '未启用';
  if (schedulerStatus.value.task_running) return '处理中';
  if ((schedulerStatus.value.failure_count || 0) >= 3) return '连续失败';
  if (schedulerStatus.value.ready_flag?.exists) return '已就绪';
  if (schedulerStatus.value.last_result === 'scan_failed') return '检查失败';
  if (schedulerStatus.value.last_result === 'trigger_failed') return '触发失败';
  if (schedulerStatus.value.last_result === 'waiting') return '等待数据';
  if (schedulerStatus.value.last_result === 'marked_ready') return '已标记';
  if (schedulerStatus.value.last_result === 'completed') return '已完成';
  return schedulerStatus.value.running ? '运行中' : '已停止';
});
const schedulerStatusTagType = computed(() => {
  if (!schedulerStatus.value?.enabled) return 'default';
  if ((schedulerStatus.value.failure_count || 0) >= 3) return 'error';
  if (schedulerStatus.value.task_running || schedulerStatus.value.ready_flag?.exists) return 'success';
  if (['scan_failed', 'trigger_failed'].includes(schedulerStatus.value.last_result || '')) return 'error';
  if (schedulerStatus.value.last_result === 'waiting') return 'warning';
  return 'info';
});
const schedulerTargetWeekText = computed(() => {
  const week = schedulerStatus.value?.target_week;
  if (!week) return '-';
  return `${week.start} 至 ${week.end}`;
});
const schedulerDirectoryRows = computed(() => {
  const directoryStatus = schedulerStatus.value?.directory_status || {};
  return Object.entries(directoryStatus).map(([name, status]) => ({
    name,
    displayName: name.replace(/^rj:/i, ''),
    ...status
  }));
});
const schedulerControlsDisabled = computed(() => !remoteForm.enabled || !remoteForm.auto_scheduler.enabled);

watch(
  () => remoteForm.enabled,
  enabled => {
    if (!enabled && remoteForm.auto_scheduler.enabled) {
      remoteForm.auto_scheduler.enabled = false;
    }
  }
);

watch(
  () => remoteForm.auto_scheduler.enabled,
  enabled => {
    if (enabled) {
      remoteForm.auto_delete_source = true;
    }
  }
);

onMounted(() => {
  setPageHeader({
    actions: [
      { key: 'config-update', kind: 'text', label: configUpdateText },
      { key: 'download-config', label: '下载配置', icon: CloudDownloadOutline, onClick: downloadConfig },
      { key: 'upload-config', label: '上传配置', icon: CloudUploadOutline, onClick: () => configInput.value?.click() }
    ]
  });
  void loadConfig();
  void loadSchedulerStatus();
});

onBeforeUnmount(() => {
  resetPageHeader();
});

async function loadConfig() {
  loading.value = true;
  try {
    const config = await apiGet<AppConfig>('/api/config/full');
    configUpdate.value = config.update;
    sourceType.value = config.source_type || 'sftp';
    warehouseType.value = config.warehouse_type || 'mysql';
    if (config.metrix) {
      metrixForm.base_url = config.metrix.base_url || '';
      metrixForm.token = config.metrix.token || '';
      metrixForm.storage_id = config.metrix.storage_id || '';
      metrixForm.database_conn_id = config.metrix.database_conn_id || '';
      metrixForm.target_database = config.metrix.target_database || '';
      metrixForm.recent_days = Number(config.metrix.recent_days) || 7;
    }
    Object.assign(dataMappingsForm, normalizeDataMappingsConfig(config.data_mappings));
    mysqlForm.host = config.mysql.host;
    mysqlForm.port = config.mysql.port;
    mysqlForm.user = config.mysql.user;
    mysqlForm.passwd = config.mysql.passwd || '';
    mysqlForm.dbname = config.mysql.dbname;
    Object.assign(remoteForm, normalizeRemoteConfig(config.remote_data));
    Object.assign(historyRetentionForm, normalizeHistoryRetentionConfig(config.history_retention));
    sheetFilters.value = [...config.sheet_filter];
    extractFields.value = normalizeExtractFields(config.extract_fields);
    resetExtractInputs();
    enforceRemoteSchedulerRules();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载配置失败');
  } finally {
    loading.value = false;
  }
}

function updateRemoteProtocol(value: string) {
  if (value === 'sftp' && (!remoteForm.port || remoteForm.port === 21)) {
    remoteForm.port = 22;
  }
  if (value === 'ftp' && (!remoteForm.port || remoteForm.port === 22)) {
    remoteForm.port = 21;
  }
}

async function saveBackend() {
  savingBackend.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/backend', {
      source_type: sourceType.value,
      warehouse_type: warehouseType.value
    });
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || '后端类型已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存后端类型失败');
  } finally {
    savingBackend.value = false;
  }
}

async function saveMetrix() {
  if (!metrixForm.base_url) {
    message.warning('请填写平台地址');
    return;
  }
  savingMetrix.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/metrix', {
      ...metrixForm,
      recent_days: Math.max(Number(metrixForm.recent_days) || 7, 1)
    });
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || 'Metrix 连接已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存 Metrix 连接失败');
  } finally {
    savingMetrix.value = false;
  }
}

async function saveMysql() {
  if (!mysqlForm.host || !mysqlForm.user || !mysqlForm.dbname) {
    message.warning('请填写完整数据库配置');
    return;
  }

  savingMysql.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/mysql', {
      ...mysqlForm,
      port: mysqlForm.port || 3306
    });
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || '数据库配置已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存数据库配置失败');
  } finally {
    savingMysql.value = false;
  }
}

function getRemotePayload(): RemoteDataConfig {
  enforceRemoteSchedulerRules();
  const autoScheduler = normalizeAutoSchedulerConfig(remoteForm.auto_scheduler);
  return {
    ...remoteForm,
    protocol: remoteForm.protocol,
    host: remoteForm.host.trim(),
    port: remoteForm.port || (remoteForm.protocol === 'sftp' ? 22 : 21),
    user: remoteForm.user.trim(),
    passwd: remoteForm.passwd || '',
    remote_dir: remoteForm.remote_dir.trim() || '/',
    passive: remoteForm.passive,
    timeout: remoteForm.timeout || 30,
    auto_delete_source: remoteForm.auto_delete_source,
    auto_scheduler: autoScheduler
  };
}

function validateRemoteForm(): boolean {
  if (!remoteForm.host || !remoteForm.user || !remoteForm.remote_dir) {
    message.warning('请填写完整远程数据源配置');
    return false;
  }
  return true;
}

async function saveRemote() {
  if (!validateRemoteForm()) return;

  savingRemote.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/remote', getRemotePayload());
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || '远程数据源配置已保存');
    await loadSchedulerStatus();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存远程数据源配置失败');
  } finally {
    savingRemote.value = false;
  }
}

function addDirectoryMapping() {
  const path = normalizeDirectoryText(newDirectoryMapping.path);
  const table = newDirectoryMapping.table.trim();
  const readyRule = newDirectoryMapping.ready_rule === 'auto' ? 'auto' : 'daily';
  if (!path || !table) {
    message.warning('请填写目录路径和暂存表名');
    return;
  }
  const exists = dataMappingsForm.directories.some(
    item => normalizeDirectoryText(item.path) === path && item.table.trim() === table && item.ready_rule === readyRule
  );
  if (exists) {
    message.warning('该目录映射已存在');
    return;
  }
  dataMappingsForm.directories.push({ path, table, ready_rule: readyRule });
  newDirectoryMapping.path = '';
  newDirectoryMapping.table = '';
  newDirectoryMapping.ready_rule = 'daily';
}

function removeDirectoryMapping(index: number) {
  dataMappingsForm.directories.splice(index, 1);
}

async function saveDirectoryMappings() {
  const config = normalizeDataMappingsConfig(dataMappingsForm);
  if (config.directories.length === 0) {
    message.warning('请至少保留一个数据目录映射');
    return;
  }

  savingDirectoryMappings.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/data-mappings', config);
    Object.assign(dataMappingsForm, config);
    configUpdate.value = result.update || configUpdate.value;
    message.success('数据目录映射已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存数据目录映射失败');
  } finally {
    savingDirectoryMappings.value = false;
  }
}

function addSchedulerDirectory() {
  const value = normalizeDirectoryText(newSchedulerDirectory.value);
  if (!value) return;
  if (remoteForm.auto_scheduler.expected_directories.includes(value)) {
    message.warning('该目录已存在');
    return;
  }
  remoteForm.auto_scheduler.expected_directories.push(value);
  newSchedulerDirectory.value = '';
}

function removeSchedulerDirectory(index: number) {
  remoteForm.auto_scheduler.expected_directories.splice(index, 1);
}

async function loadSchedulerStatus() {
  loadingSchedulerStatus.value = true;
  try {
    schedulerStatus.value = await apiGet<RemoteSchedulerStatus>('/api/remote/scheduler/status');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载自动调度状态失败');
  } finally {
    loadingSchedulerStatus.value = false;
  }
}

async function triggerSchedulerCheck() {
  triggeringScheduler.value = true;
  try {
    const result = await apiPost<{ success: boolean; message?: string; status?: RemoteSchedulerStatus }>(
      '/api/remote/scheduler/trigger'
    );
    if (result.status) {
      schedulerStatus.value = result.status;
    } else {
      await loadSchedulerStatus();
    }
    message[result.success ? 'success' : 'warning'](result.message || '自动调度检查已执行');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '自动调度检查失败');
  } finally {
    triggeringScheduler.value = false;
  }
}

async function testRemote() {
  if (!validateRemoteForm()) return;

  testingRemote.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/remote/test', getRemotePayload());
    message[result.success ? 'success' : 'error'](result.message || '远程连接测试完成');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '远程连接测试失败');
  } finally {
    testingRemote.value = false;
  }
}

async function testDatabase() {
  testingDb.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/database/test');
    message[result.success ? 'success' : 'error'](result.message || '连接测试完成');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '数据库连接测试失败');
  } finally {
    testingDb.value = false;
  }
}

async function saveHistoryRetention() {
  savingHistoryRetention.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/history-retention', {
      enabled: historyRetentionForm.enabled,
      keep_count: Math.max(Number(historyRetentionForm.keep_count) || 0, 0)
    });
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || '处理历史保留配置已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存处理历史保留配置失败');
  } finally {
    savingHistoryRetention.value = false;
  }
}

function addSheetFilter() {
  const value = newSheetFilter.value.trim();
  if (!value) return;
  if (sheetFilters.value.includes(value)) {
    message.warning('该规则已存在');
    return;
  }
  sheetFilters.value.push(value);
  newSheetFilter.value = '';
}

function removeSheetFilter(index: number) {
  sheetFilters.value.splice(index, 1);
}

async function saveSheetFilter() {
  savingSheetFilter.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/sheet-filter', sheetFilters.value);
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || '过滤规则已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存过滤规则失败');
  } finally {
    savingSheetFilter.value = false;
  }
}

function addFieldMapping() {
  extractFields.value.push({ Field: '', Type: 'string', Extract: [] });
  resetExtractInputs();
}

function removeFieldMapping(index: number) {
  extractFields.value.splice(index, 1);
  resetExtractInputs();
}

function addExtract(index: number) {
  const value = (newExtractValues[index] || '').trim();
  if (!value) return;

  const field = extractFields.value[index];
  if (!field) return;

  if (field.Extract.includes(value)) {
    message.warning('该提取来源已存在');
    return;
  }

  field.Extract.push(value);
  newExtractValues[index] = '';
}

function removeExtract(fieldIndex: number, extractIndex: number) {
  extractFields.value[fieldIndex]?.Extract.splice(extractIndex, 1);
}

async function saveExtractFields() {
  const fields = extractFields.value
    .map(field => ({
      ...field,
      Field: field.Field.trim(),
      Type: field.Type || 'string',
      Extract: uniqueStrings(field.Extract)
    }))
    .filter(field => field.Field);

  if (fields.length === 0) {
    message.warning('请至少保留一个有效字段');
    return;
  }

  savingExtractFields.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/extract-fields', fields);
    extractFields.value = fields;
    resetExtractInputs();
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || '字段配置已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存字段配置失败');
  } finally {
    savingExtractFields.value = false;
  }
}

async function changePassword() {
  if (passwordForm.new_password.length < 4) {
    message.warning('新密码不能少于 4 位');
    return;
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    message.warning('两次输入的新密码不一致');
    return;
  }

  changingPassword.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/change-password', {
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password
    });
    passwordForm.current_password = '';
    passwordForm.new_password = '';
    passwordForm.confirm_password = '';
    message.success(result.message || '密码已修改');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '修改密码失败');
  } finally {
    changingPassword.value = false;
  }
}

async function downloadConfig() {
  try {
    const filename = 'Configure.json';
    const result = await downloadGet('/api/config/download', filename);
    if (result.saved) {
      showDownloadCompleteDialog(dialog, filename, result.path);
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '下载配置失败');
  }
}

async function uploadConfigFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);
  try {
    const result = await upload<ApiMessage>('/api/config/upload', formData);
    message.success(result.message || '配置文件已上传');
    await loadConfig();
  } catch (error) {
    message.error(error instanceof Error ? error.message : '上传配置失败');
  }
}

function normalizeRemoteConfig(config: RemoteDataConfig | undefined): RemoteDataConfig {
  const protocol = config?.protocol === 'ftp' ? 'ftp' : 'sftp';
  const autoScheduler = normalizeAutoSchedulerConfig(config?.auto_scheduler);
  return {
    enabled: Boolean(config?.enabled),
    protocol,
    host: config?.host || '',
    port: config?.port || (protocol === 'sftp' ? 22 : 21),
    user: config?.user || '',
    passwd: config?.passwd || '',
    remote_dir: config?.remote_dir || '/',
    passive: config?.passive ?? true,
    timeout: config?.timeout || 30,
    auto_delete_source: Boolean(config?.auto_delete_source) || autoScheduler.enabled,
    auto_scheduler: autoScheduler
  };
}

function normalizeDataMappingsConfig(config: DataMappingsConfig | undefined): DataMappingsConfig {
  const directories: DataDirectoryMapping[] = [];
  const seen = new Set<string>();
  for (const item of config?.directories || []) {
    const path = normalizeDirectoryText(item.path || '');
    const table = String(item.table || '').trim();
    const readyRule = item.ready_rule === 'auto' ? 'auto' : 'daily';
    if (!path || !table) continue;
    const key = `${path}\n${table}\n${readyRule}`;
    if (seen.has(key)) continue;
    seen.add(key);
    directories.push({ path, table, ready_rule: readyRule });
  }
  if (directories.length === 0) {
    directories.push(
      { path: '4G', table: '4G_UD', ready_rule: 'daily' },
      { path: '5G', table: '5G_UD', ready_rule: 'daily' }
    );
  }
  return {
    directories,
    table_field_mappings: config?.table_field_mappings || {}
  };
}

function normalizeAutoSchedulerConfig(config: RemoteAutoSchedulerConfig | undefined): RemoteAutoSchedulerConfig {
  return {
    enabled: Boolean(config?.enabled),
    check_interval_hours: Math.max(Number(config?.check_interval_hours ?? 1) || 1, 1),
    expected_directories: uniqueStrings(config?.expected_directories || []).map(normalizeDirectoryText).filter(Boolean),
    week_offset: Number.isFinite(Number(config?.week_offset)) ? Number(config?.week_offset) : 0
  };
}

function enforceRemoteSchedulerRules() {
  if (!remoteForm.enabled) {
    remoteForm.auto_scheduler.enabled = false;
    return;
  }
  if (!remoteForm.auto_scheduler.enabled) return;
  remoteForm.auto_delete_source = true;
  remoteForm.auto_scheduler.check_interval_hours = Math.max(Number(remoteForm.auto_scheduler.check_interval_hours) || 1, 1);
  remoteForm.auto_scheduler.expected_directories = uniqueStrings(remoteForm.auto_scheduler.expected_directories)
    .map(normalizeDirectoryText)
    .filter(Boolean);
}

function normalizeDirectoryText(value: string): string {
  return value.replace(/\\/g, '/').trim().replace(/^\/+|\/+$/g, '');
}

function normalizeHistoryRetentionConfig(config: HistoryRetentionConfig | undefined): HistoryRetentionConfig {
  return {
    enabled: Boolean(config?.enabled),
    keep_count: Math.max(Number(config?.keep_count ?? 20) || 0, 0)
  };
}

function normalizeExtractFields(fields: Array<Record<string, unknown>>): ExtractFieldConfig[] {
  return fields.map(field => {
    const extract = Array.isArray(field.Extract) ? uniqueStrings(field.Extract) : [];
    return {
      ...field,
      Field: String(field.Field || ''),
      Type: typeof field.Type === 'string' && field.Type ? field.Type : 'string',
      Extract: extract
    };
  });
}

function uniqueStrings(values: unknown[]): string[] {
  return Array.from(
    new Set(
      values
        .map(value => String(value || '').trim())
        .filter(Boolean)
    )
  );
}

function resetExtractInputs() {
  for (const key of Object.keys(newExtractValues)) {
    delete newExtractValues[Number(key)];
  }
  extractFields.value.forEach((_, index) => {
    newExtractValues[index] = '';
  });
}
</script>
