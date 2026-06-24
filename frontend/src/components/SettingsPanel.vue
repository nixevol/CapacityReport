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
                  <p class="form-hint">主数据源和数据仓库可独立选择；CellData 单独配置。</p>
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
                  <p class="form-hint">填写 Metrix 平台连接信息。</p>
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

              <n-card title="CellData 数据库配置" size="small" class="work-card">
                <n-form label-placement="top">
                  <n-grid :cols="12" :x-gap="12">
                    <n-gi :span="8">
                      <n-form-item label="主机地址">
                        <n-input v-model:value="cellDataMysqlForm.host" placeholder="localhost" />
                      </n-form-item>
                    </n-gi>
                    <n-gi :span="4">
                      <n-form-item label="端口">
                        <n-input-number v-model:value="cellDataMysqlForm.port" class="full-width" :min="1" :max="65535" />
                      </n-form-item>
                    </n-gi>
                  </n-grid>
                  <n-form-item label="数据库名">
                    <n-input v-model:value="cellDataMysqlForm.dbname" placeholder="celldata" />
                  </n-form-item>
                  <n-grid :cols="12" :x-gap="12">
                    <n-gi :span="6">
                      <n-form-item label="用户名">
                        <n-input v-model:value="cellDataMysqlForm.user" placeholder="root" />
                      </n-form-item>
                    </n-gi>
                    <n-gi :span="6">
                      <n-form-item label="密码">
                        <n-input v-model:value="cellDataMysqlForm.passwd" type="password" show-password-on="click" />
                      </n-form-item>
                    </n-gi>
                  </n-grid>
                  <p class="form-hint">填写 CellData 数据库连接；可与主数据库相同。</p>
                </n-form>

                <template #footer>
                  <n-space justify="end">
                    <n-button type="primary" :loading="savingCellDataMysql" @click="saveCellDataMysql">保存配置</n-button>
                    <n-button :loading="testingCellDataDb" @click="testCellDataDatabase">测试连接</n-button>
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
                  <p class="form-hint">设置任务历史保留数量；0 表示不保留。</p>
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
                <p class="form-hint">填写容量数据来源；可选择处理成功后删除源文件。</p>
              </n-form>

              <template #footer>
                <n-space justify="end">
                  <n-button type="primary" :loading="savingRemote" @click="saveRemote">保存配置</n-button>
                  <n-button :loading="testingRemote" @click="testRemote">测试连接</n-button>
                </n-space>
              </template>
            </n-card>

            <n-card title="CellData 数据源" size="small" class="work-card settings-remote-card">
              <n-form label-placement="top">
                <div class="remote-connection-row">
                  <n-form-item label="协议">
                    <n-select
                      v-model:value="cellDataRemoteForm.protocol"
                      :options="remoteProtocolOptions"
                      @update:value="updateCellDataRemoteProtocol"
                    />
                  </n-form-item>
                  <n-form-item label="服务器地址">
                    <n-input v-model:value="cellDataRemoteForm.host" placeholder="192.168.1.10" />
                  </n-form-item>
                  <n-form-item label="端口">
                    <n-input-number v-model:value="cellDataRemoteForm.port" class="full-width" :min="1" :max="65535" />
                  </n-form-item>
                  <n-form-item label="超时秒数">
                    <n-input-number v-model:value="cellDataRemoteForm.timeout" class="full-width" :min="1" :max="600" />
                  </n-form-item>
                  <n-form-item label="FTP 被动模式" class="remote-passive-field">
                    <n-switch v-model:value="cellDataRemoteForm.passive" :disabled="cellDataRemoteForm.protocol !== 'ftp'" />
                  </n-form-item>
                </div>
                <n-grid :cols="12" :x-gap="12">
                  <n-gi :span="6">
                    <n-form-item label="用户名">
                      <n-input v-model:value="cellDataRemoteForm.user" placeholder="remote user" />
                    </n-form-item>
                  </n-gi>
                  <n-gi :span="6">
                    <n-form-item label="密码">
                      <n-input v-model:value="cellDataRemoteForm.passwd" type="password" show-password-on="click" />
                    </n-form-item>
                  </n-gi>
                </n-grid>
                <n-form-item label="远程目录">
                  <n-input v-model:value="cellDataRemoteForm.remote_dir" placeholder="/" />
                </n-form-item>
                <n-form-item label="启用 CellData 数据源">
                  <n-switch v-model:value="cellDataRemoteForm.enabled" />
                </n-form-item>
                <p class="form-hint">填写 CellData 文件来源。</p>
              </n-form>

              <template #footer>
                <n-space justify="end">
                  <n-button type="primary" :loading="savingCellDataRemote" @click="saveCellDataRemote">保存配置</n-button>
                  <n-button :loading="testingCellDataRemote" @click="testCellDataRemote">测试连接</n-button>
                  <n-button @click="openCellDataSettingsModal">规则设置</n-button>
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
                <p class="form-hint">启用后按目标周检查文件完整性，满足条件后自动处理。</p>
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
                  <p class="form-hint">配置源目录对应的暂存表和检查规则。</p>
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
                  <p class="form-hint">这些 Sheet 会跳过。</p>
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
                  <p class="form-hint">把源文件列名映射为数据库字段。</p>
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

    <n-modal
      v-model:show="cellDataHelpVisible"
      preset="card"
      class="cell-data-help-modal"
      title="扫描路径说明"
      style="width: min(520px, calc(100vw - 32px))"
    >
      <n-scrollbar class="cell-data-help-scroll">
        <section class="cell-data-help-section">
          <h4>路径模板</h4>
          <p>每行填写一个扫描目录。系统会在目录下继续识别 700M、2.6G 等子目录。</p>
          <code>/网优日常优化数据文档/日常性能报表/{maxyear}年/300表</code>
        </section>
        <section class="cell-data-help-section">
          <h4>占位符</h4>
          <p><strong>{maxyear}</strong>：扫描同级年份目录并取最大年份。</p>
          <p><strong>{yyyy}</strong>：当前年份。</p>
          <p><strong>{yyyymm}</strong>：当前年月。</p>
          <p><strong>{yyyymmdd}</strong>：当前日期。</p>
        </section>
        <section class="cell-data-help-section">
          <h4>高级正则</h4>
          <p><strong>年份目录正则</strong>：识别年份目录，默认匹配 2026年。</p>
          <p><strong>文件名正则</strong>：筛选 ZIP 文件，默认匹配 Result_300_ 开头。</p>
          <p><strong>时间戳正则</strong>：从 ZIP 文件名末尾提取文件时间。</p>
        </section>
        <section class="cell-data-help-section">
          <h4>多目录示例</h4>
          <code>/网优日常优化数据文档/日常性能报表/{maxyear}年/300表</code>
          <code>/网优日常优化数据文档/日常性能报表/{maxyear}年/cellinfo</code>
        </section>
      </n-scrollbar>
    </n-modal>

    <n-modal
      v-model:show="cellDataSettingsVisible"
      preset="card"
      class="cell-data-settings-modal"
      title="CellData 规则设置"
      style="width: min(860px, calc(100vw - 32px))"
      @after-enter="layoutCellDataEditor"
      @after-leave="disposeCellDataEditor"
    >
      <div class="cell-data-settings-body">
        <section class="cell-data-settings-section">
          <div class="cell-data-section-title">
            <strong>扫描路径</strong>
            <n-button quaternary circle size="small" title="查看说明" @click="cellDataHelpVisible = true">
              <template #icon>
                <n-icon><InformationCircleOutline /></n-icon>
              </template>
            </n-button>
          </div>
          <div class="cell-data-path-list">
            <div v-for="(path, index) in cellDataScanPaths" :key="`${path}-${index}`" class="cell-data-path-row">
              <n-input v-model:value="cellDataScanPaths[index]" size="small" placeholder="/.../{maxyear}年/300表" />
              <n-button quaternary circle size="small" type="error" @click="removeCellDataScanPath(index)">
                <template #icon>
                  <n-icon><CloseOutline /></n-icon>
                </template>
              </n-button>
            </div>
          </div>
          <n-input-group>
            <n-input v-model:value="newCellDataScanPath" placeholder="扫描路径模板" @keydown.enter.prevent="addCellDataScanPath" />
            <n-button @click="addCellDataScanPath">添加</n-button>
          </n-input-group>
        </section>

        <section class="cell-data-settings-section">
          <div class="cell-data-section-title">
            <strong>高级匹配</strong>
          </div>
          <n-grid :cols="12" :x-gap="12">
            <n-gi :span="4">
              <n-form-item label="年份目录正则">
                <n-input v-model:value="cellDataRegexForm.year_dir_regex" />
              </n-form-item>
            </n-gi>
            <n-gi :span="4">
              <n-form-item label="文件名正则">
                <n-input v-model:value="cellDataRegexForm.file_name_regex" />
              </n-form-item>
            </n-gi>
            <n-gi :span="4">
              <n-form-item label="时间戳正则">
                <n-input v-model:value="cellDataRegexForm.file_time_regex" />
              </n-form-item>
            </n-gi>
          </n-grid>
        </section>

        <section class="cell-data-settings-section">
          <div class="cell-data-section-title">
            <strong>映射规则 JSON</strong>
            <n-space size="small">
              <n-button size="small" @click="formatCellDataMapping">格式化</n-button>
              <n-button size="small" :loading="validatingCellDataSettings" @click="validateCellDataSettings">校验</n-button>
              <n-button size="small" @click="restoreDefaultCellDataMapping">恢复默认</n-button>
            </n-space>
          </div>
          <div ref="cellDataEditorHost" class="cell-data-json-editor"></div>
        </section>
      </div>

      <template #footer>
        <n-space justify="end">
          <n-button @click="cellDataSettingsVisible = false">取消</n-button>
          <n-button type="primary" :loading="savingCellDataSettings" @click="saveCellDataSettings">保存规则</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from 'vue';
import { useDialog, useMessage, type SelectOption } from 'naive-ui';
import { CloseOutline, CloudDownloadOutline, CloudUploadOutline, InformationCircleOutline } from '@vicons/ionicons5';
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api.js';
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import 'monaco-editor/esm/vs/language/json/monaco.contribution';

import { apiGet, apiPost, downloadGet, upload } from '../api/client';
import type {
  ApiMessage,
  AppConfig,
  CellDataConfig,
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

type MonacoGlobal = typeof globalThis & {
  MonacoEnvironment?: {
    getWorker: (_moduleId: string, _label: string) => Worker;
  };
};

(globalThis as MonacoGlobal).MonacoEnvironment = {
  getWorker: () => new editorWorker()
};

const message = useMessage();
const dialog = useDialog();
const configInput = ref<HTMLInputElement | null>(null);
const configUpdate = ref('');
const configUpdateText = computed(() => `更新时间：${configUpdate.value || '-'}`);
const loading = ref(false);
const testingDb = ref(false);
const testingRemote = ref(false);
const testingCellDataDb = ref(false);
const testingCellDataRemote = ref(false);
const loadingSchedulerStatus = ref(false);
const triggeringScheduler = ref(false);
const savingMysql = ref(false);
const savingRemote = ref(false);
const savingCellDataMysql = ref(false);
const savingCellDataRemote = ref(false);
const savingCellDataSettings = ref(false);
const validatingCellDataSettings = ref(false);
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
const newCellDataScanPath = ref('');
const cellDataHelpVisible = ref(false);
const cellDataSettingsVisible = ref(false);
const cellDataScanPaths = ref<string[]>([]);
const cellDataMappingText = ref('');
const cellDataEditorHost = ref<HTMLDivElement | null>(null);
const cellDataEditor = shallowRef<monaco.editor.IStandaloneCodeEditor | null>(null);
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

const cellDataRemoteForm = reactive<RemoteDataConfig>({
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

const cellDataRegexForm = reactive({
  year_dir_regex: '(?P<year>\\\\d{4})年',
  file_name_regex: '^Result_300_.*\\\\.zip$',
  file_time_regex: '(?P<timestamp>\\\\d{14})(?=\\\\.zip$)'
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

const cellDataMysqlForm = reactive({
  host: '',
  port: 3306 as number | null,
  user: '',
  passwd: '',
  dbname: 'celldata'
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
  disposeCellDataEditor();
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
    Object.assign(cellDataRemoteForm, normalizeRemoteConfig(config.cell_data?.remote_data, '/'));
    Object.assign(cellDataMysqlForm, normalizeCellDataMysqlConfig(config.cell_data?.mysql));
    cellDataScanPaths.value = normalizeCellDataScanPaths(config.cell_data?.scan_paths);
    cellDataRegexForm.year_dir_regex = config.cell_data?.year_dir_regex || '(?P<year>\\\\d{4})年';
    cellDataRegexForm.file_name_regex = config.cell_data?.file_name_regex || '^Result_300_.*\\\\.zip$';
    cellDataRegexForm.file_time_regex = config.cell_data?.file_time_regex || '(?P<timestamp>\\\\d{14})(?=\\\\.zip$)';
    cellDataMappingText.value = JSON.stringify(config.cell_data?.mapping || {}, null, 2);
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

function updateCellDataRemoteProtocol(value: string) {
  if (value === 'sftp' && (!cellDataRemoteForm.port || cellDataRemoteForm.port === 21)) {
    cellDataRemoteForm.port = 22;
  }
  if (value === 'ftp' && (!cellDataRemoteForm.port || cellDataRemoteForm.port === 22)) {
    cellDataRemoteForm.port = 21;
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

async function saveCellDataMysql() {
  if (!cellDataMysqlForm.host || !cellDataMysqlForm.user || !cellDataMysqlForm.dbname) {
    message.warning('请填写完整 CellData 数据库配置');
    return;
  }

  savingCellDataMysql.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/cell-data/mysql', {
      ...cellDataMysqlForm,
      port: cellDataMysqlForm.port || 3306
    });
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || 'CellData 数据库配置已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存 CellData 数据库配置失败');
  } finally {
    savingCellDataMysql.value = false;
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

function getCellDataRemotePayload(): RemoteDataConfig {
  return {
    ...cellDataRemoteForm,
    protocol: cellDataRemoteForm.protocol,
    host: cellDataRemoteForm.host.trim(),
    port: cellDataRemoteForm.port || (cellDataRemoteForm.protocol === 'sftp' ? 22 : 21),
    user: cellDataRemoteForm.user.trim(),
    passwd: cellDataRemoteForm.passwd || '',
    remote_dir: cellDataRemoteForm.remote_dir.trim() || '/',
    passive: cellDataRemoteForm.passive,
    timeout: cellDataRemoteForm.timeout || 30,
    auto_delete_source: false,
    auto_scheduler: {
      enabled: false,
      check_interval_hours: 1,
      expected_directories: [],
      week_offset: 0
    }
  };
}

function validateRemoteForm(): boolean {
  if (!remoteForm.host || !remoteForm.user || !remoteForm.remote_dir) {
    message.warning('请填写完整远程数据源配置');
    return false;
  }
  return true;
}

function validateCellDataRemoteForm(): boolean {
  if (!cellDataRemoteForm.host || !cellDataRemoteForm.user || !cellDataRemoteForm.remote_dir) {
    message.warning('请填写完整 CellData 远程数据源配置');
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

async function saveCellDataRemote() {
  if (!validateCellDataRemoteForm()) return;

  savingCellDataRemote.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/cell-data/remote', getCellDataRemotePayload());
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || 'CellData 远程数据源配置已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存 CellData 远程数据源配置失败');
  } finally {
    savingCellDataRemote.value = false;
  }
}

function addCellDataScanPath() {
  const value = normalizeDirectoryText(newCellDataScanPath.value);
  if (!value) return;
  if (cellDataScanPaths.value.includes(value)) {
    message.warning('该扫描路径已存在');
    return;
  }
  cellDataScanPaths.value.push(value);
  newCellDataScanPath.value = '';
}

function removeCellDataScanPath(index: number) {
  cellDataScanPaths.value.splice(index, 1);
}

function getCellDataSettingsPayload() {
  let mapping: Record<string, unknown>;
  try {
    mapping = JSON.parse(getCellDataMappingText() || '{}') as Record<string, unknown>;
  } catch {
    throw new Error('映射规则不是有效 JSON');
  }
  return {
    scan_paths: normalizeCellDataScanPaths(cellDataScanPaths.value),
    year_dir_regex: cellDataRegexForm.year_dir_regex,
    file_name_regex: cellDataRegexForm.file_name_regex,
    file_time_regex: cellDataRegexForm.file_time_regex,
    mapping
  };
}

async function validateCellDataSettings() {
  validatingCellDataSettings.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/cell-data/settings/validate', getCellDataSettingsPayload());
    message[result.success ? 'success' : 'error'](result.message || '校验完成');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '校验失败');
  } finally {
    validatingCellDataSettings.value = false;
  }
}

async function restoreDefaultCellDataMapping() {
  try {
    const mapping = await apiGet<Record<string, unknown>>('/api/config/cell-data/mapping/default');
    setCellDataMappingText(JSON.stringify(mapping, null, 2));
    message.success('已恢复默认映射');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '恢复默认映射失败');
  }
}

async function saveCellDataSettings() {
  savingCellDataSettings.value = true;
  try {
    const payload = getCellDataSettingsPayload();
    const result = await apiPost<ApiMessage>('/api/config/cell-data/settings', payload);
    cellDataScanPaths.value = normalizeCellDataScanPaths(payload.scan_paths);
    setCellDataMappingText(JSON.stringify(payload.mapping, null, 2));
    configUpdate.value = result.update || configUpdate.value;
    message.success(result.message || 'CellData 规则已保存');
  } catch (error) {
    message.error(error instanceof Error ? error.message : '保存 CellData 规则失败');
  } finally {
    savingCellDataSettings.value = false;
  }
}

function openCellDataSettingsModal() {
  cellDataSettingsVisible.value = true;
  void nextTick(createCellDataEditor);
}

function createCellDataEditor() {
  if (!cellDataEditorHost.value || cellDataEditor.value) {
    layoutCellDataEditor();
    return;
  }
  cellDataEditor.value = monaco.editor.create(cellDataEditorHost.value, {
    value: cellDataMappingText.value || '{}',
    language: 'json',
    theme: currentEditorTheme(),
    fontSize: 13,
    fontFamily: "Consolas, 'Courier New', monospace",
    minimap: { enabled: false },
    automaticLayout: true,
    scrollBeyondLastLine: false,
    wordWrap: 'on',
    tabSize: 2,
    insertSpaces: true,
    formatOnPaste: true,
    formatOnType: true
  });
}

function disposeCellDataEditor() {
  if (cellDataEditor.value) {
    cellDataMappingText.value = cellDataEditor.value.getValue();
    cellDataEditor.value.dispose();
    cellDataEditor.value = null;
  }
}

function layoutCellDataEditor() {
  void nextTick(() => cellDataEditor.value?.layout());
}

function getCellDataMappingText(): string {
  return cellDataEditor.value?.getValue() ?? cellDataMappingText.value;
}

function setCellDataMappingText(value: string) {
  cellDataMappingText.value = value;
  if (cellDataEditor.value) {
    cellDataEditor.value.setValue(value);
  }
}

async function formatCellDataMapping() {
  try {
    const formatted = JSON.stringify(JSON.parse(getCellDataMappingText() || '{}'), null, 2);
    setCellDataMappingText(formatted);
    await nextTick();
    await cellDataEditor.value?.getAction('editor.action.formatDocument')?.run();
  } catch {
    message.error('映射规则不是有效 JSON');
  }
}

function currentEditorTheme(): string {
  return document.documentElement.dataset.theme === 'dark' ? 'vs-dark' : 'vs';
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

async function testCellDataRemote() {
  if (!validateCellDataRemoteForm()) return;

  testingCellDataRemote.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/cell-data/remote/test', getCellDataRemotePayload());
    message[result.success ? 'success' : 'error'](result.message || 'CellData 远程连接测试完成');
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'CellData 远程连接测试失败');
  } finally {
    testingCellDataRemote.value = false;
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

async function testCellDataDatabase() {
  testingCellDataDb.value = true;
  try {
    const result = await apiPost<ApiMessage>('/api/config/cell-data/mysql/test', {
      ...cellDataMysqlForm,
      port: cellDataMysqlForm.port || 3306
    });
    message[result.success ? 'success' : 'error'](result.message || 'CellData 数据库连接测试完成');
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'CellData 数据库连接测试失败');
  } finally {
    testingCellDataDb.value = false;
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

function normalizeRemoteConfig(config: RemoteDataConfig | undefined, defaultRemoteDir = '/'): RemoteDataConfig {
  const protocol = config?.protocol === 'ftp' ? 'ftp' : 'sftp';
  const autoScheduler = normalizeAutoSchedulerConfig(config?.auto_scheduler);
  return {
    enabled: Boolean(config?.enabled),
    protocol,
    host: config?.host || '',
    port: config?.port || (protocol === 'sftp' ? 22 : 21),
    user: config?.user || '',
    passwd: config?.passwd || '',
    remote_dir: config?.remote_dir || defaultRemoteDir,
    passive: config?.passive ?? true,
    timeout: config?.timeout || 30,
    auto_delete_source: Boolean(config?.auto_delete_source) || autoScheduler.enabled,
    auto_scheduler: autoScheduler
  };
}

function normalizeCellDataMysqlConfig(config: CellDataConfig['mysql'] | undefined) {
  return {
    host: config?.host || 'localhost',
    port: config?.port || 3306,
    user: config?.user || 'root',
    passwd: config?.passwd || '',
    dbname: config?.dbname || 'celldata'
  };
}

function normalizeCellDataScanPaths(paths: string[] | undefined): string[] {
  const normalized = uniqueStrings(paths || [])
    .map(path => path.replace(/\\/g, '/').trim())
    .filter(Boolean);
  return normalized.length
    ? normalized
    : ['/网优日常优化数据文档/日常性能报表/{maxyear}年/300表'];
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
