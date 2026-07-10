<template>
  <div class="other-settings">
    <!-- 内部销售码平台开关（仅管理员可见；控制侧栏「内部销售码管理」菜单，改后即生效、免登服务器） -->
    <section v-if="isAdmin" class="card">
      <h3 class="card-title">内部销售码管理平台</h3>
      <p class="tip muted" style="margin-top:0">
        开启后，管理员侧栏出现「内部销售码管理」菜单（生成 / 核销 / 查询）。仅用于内部销售码业务的实例开启即可。
      </p>
      <div class="form-row">
        <span class="ilabel">启用平台</span>
        <el-switch v-model="salesEnabled" :loading="savingSales" @change="onToggleSales" />
        <span class="muted hint">{{ salesEnabled ? '已启用（侧栏可见）' : '已关闭' }}</span>
      </div>
    </section>

    <!-- 外部留言讨论区开关（仅管理员；开启后公开页 /forum 可访问、侧栏出现管理菜单） -->
    <section v-if="isAdmin" class="card">
      <h3 class="card-title">外部留言讨论区</h3>
      <p class="tip muted" style="margin-top:0">
        开启后，外部用户可通过公开链接 <b>/forum</b> 注册留言（邮箱验证码，需配置下方 SMTP），
        内部侧栏出现「留言讨论区」管理菜单。关闭后公开页显示已关闭。
      </p>
      <div class="form-row">
        <span class="ilabel">启用留言区</span>
        <el-switch v-model="discussEnabled" :loading="savingDiscuss" @change="onToggleDiscuss" />
        <span class="muted hint">{{ discussEnabled ? '已开启（公开页可访问）' : '已关闭' }}</span>
      </div>
    </section>

    <!-- SMTP 邮件服务器（留言区验证码发送用；密码只写不回显） -->
    <section v-if="isAdmin" class="card">
      <h3 class="card-title">SMTP 邮件服务器</h3>
      <p class="tip muted" style="margin-top:0">
        留言区注册/登录验证码通过此邮箱发送。未配置时验证码仅打印到服务器日志（仅适合本地测试）。
      </p>
      <div class="form-row">
        <span class="ilabel">服务器</span>
        <el-input v-model="smtp.host" placeholder="如 smtp.exmail.qq.com" style="width: 240px" clearable />
        <el-input-number v-model="smtp.port" :min="1" :max="65535" controls-position="right" style="width: 110px" />
        <el-checkbox v-model="smtp.ssl">SSL</el-checkbox>
      </div>
      <div class="form-row">
        <span class="ilabel">用户名</span>
        <el-input v-model="smtp.username" placeholder="邮箱账号" style="width: 240px" clearable />
      </div>
      <div class="form-row">
        <span class="ilabel">密码</span>
        <el-input v-model="smtpPassword" type="password" show-password
          :placeholder="smtp.password_set ? '已配置（留空保持不变）' : '邮箱密码 / 授权码'" style="width: 240px" />
      </div>
      <div class="form-row">
        <span class="ilabel">发件人</span>
        <el-input v-model="smtp.sender" placeholder="留空则用用户名" style="width: 240px" clearable />
      </div>
      <div class="form-row">
        <span class="ilabel"></span>
        <el-button type="primary" :loading="savingSmtp" @click="saveSmtp">保存</el-button>
        <el-input v-model="smtpTestTo" placeholder="测试收件邮箱" style="width: 200px" clearable />
        <el-button :loading="testingSmtp" @click="testSmtp">发送测试邮件</el-button>
      </div>
    </section>

    <!-- 飞书机器人应用：本实例独立的 App ID/Secret（DB 优先于 .env，实现各实例独立机器人） -->
    <section class="card">
      <h3 class="card-title">飞书机器人应用</h3>
      <p class="tip muted" style="margin-top:0">
        配置本实例使用的飞书自建应用凭证（登录、群通知、催办私聊均用此机器人）。在此配置优先于服务器 .env；
        留空则回退 .env 默认。各实例配各自的应用即可独立管理、互不冲突。
      </p>
      <div class="form-row">
        <span class="ilabel">App ID</span>
        <el-input v-model="feishuAppId" :disabled="!isAdmin" placeholder="cli_ 开头" style="width: 320px" clearable />
      </div>
      <div class="form-row">
        <span class="ilabel">App Secret</span>
        <el-input
          v-model="feishuSecret" :disabled="!isAdmin" type="password" show-password
          :placeholder="secretSet ? '已配置（留空则保持不变）' : '请输入 App Secret'" style="width: 320px"
        />
      </div>
      <div class="form-row">
        <span class="ilabel"></span>
        <el-button type="primary" :loading="savingFeishu" :disabled="!isAdmin" @click="saveFeishuApp">保存</el-button>
        <span v-if="secretSet" class="muted hint ok">✓ 已配置密钥</span>
        <span v-if="!isAdmin" class="muted hint">（仅管理员可修改）</span>
      </div>
    </section>

    <!-- 内部销售码生成二级密码（仅 sales 租户实例显示） -->
    <section v-if="branding.data.sales_code_enabled" class="card">
      <h3 class="card-title">内部销售码生成密码</h3>
      <p class="tip muted" style="margin-top:0">
        生成内部销售码时需要的二级密码。初始为 <b>888888</b>，建议尽快修改；修改后立即生效。
      </p>
      <div class="form-row">
        <span class="ilabel">新密码</span>
        <el-input v-model="newPwd" :disabled="!isAdmin" type="password" show-password placeholder="至少 4 位" style="width: 320px" />
      </div>
      <div class="form-row">
        <span class="ilabel">确认密码</span>
        <el-input
          v-model="confirmPwd" :disabled="!isAdmin" type="password" show-password
          placeholder="再次输入" style="width: 320px" @keyup.enter="saveGenPwd"
        />
      </div>
      <div class="form-row">
        <span class="ilabel"></span>
        <el-button type="primary" :loading="savingPwd" :disabled="!isAdmin" @click="saveGenPwd">保存</el-button>
        <span v-if="genPwdIsDefault" class="muted hint warn">⚠ 当前仍为初始密码</span>
        <span v-else class="muted hint ok">✓ 已修改</span>
        <span v-if="!isAdmin" class="muted hint">（仅管理员可修改）</span>
      </div>
    </section>

    <section class="card">
      <h3 class="card-title">数据备份</h3>
      <p class="tip muted" style="margin-top:0">
        导出当前全部数据为 JSON 快照文件，可复制到其他环境上传导入。导入为<b>全量替换</b>——会清空并覆盖目标环境的现有数据。
      </p>
      <div class="backup-actions">
        <el-button type="primary" :icon="Download" :loading="exporting" :disabled="!isAdmin" @click="doExport">
          导出数据
        </el-button>
        <el-button :icon="Upload" :loading="importing" :disabled="!isAdmin" @click="triggerImport">
          导入数据
        </el-button>
        <input ref="fileInput" type="file" accept=".json,application/json" style="display:none" @change="onFileChosen" />
        <span v-if="!isAdmin" class="muted hint">（仅管理员可操作）</span>
      </div>
      <!-- 从 Excel 批量导入项目（周会跟进清单格式）：按行新增，追加不覆盖现有数据 -->
      <p class="tip muted">
        从 Excel（周会跟进清单格式：含「待办事项」「负责人」等列）批量导入项目——按行<b>新增</b>，追加导入、不影响现有数据。
      </p>
      <div class="backup-actions">
        <el-button :icon="Upload" :loading="importingExcel" :disabled="!isAdmin" @click="triggerExcelImport">
          从 Excel 导入项目
        </el-button>
        <input ref="excelInput" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" style="display:none" @change="onExcelChosen" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Upload } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useBrandingStore } from '@/stores/branding'
import { settingsApi, salesCodeApi } from '@/api/resources'
import type { SmtpConfig } from '@/types'

const auth = useAuthStore()
const branding = useBrandingStore()
const isAdmin = computed(() => auth.currentUser?.role === 'admin')

/* 内部销售码平台开关（DB 运行时开关，改后刷新品牌→侧栏菜单即时增减） */
const salesEnabled = ref(false)
const savingSales = ref(false)

async function loadSalesEnabled() {
  if (!isAdmin.value) return
  try {
    salesEnabled.value = (await settingsApi.getSalesCodeEnabled()).enabled
  } catch {
    salesEnabled.value = branding.data.sales_code_enabled
  }
}

async function onToggleSales(val: string | number | boolean) {
  const next = Boolean(val)
  savingSales.value = true
  try {
    salesEnabled.value = (await settingsApi.setSalesCodeEnabled(next)).enabled
    await branding.fetchBranding()  // 刷新品牌：侧栏菜单立即出现/消失，无需重新登录
    ElMessage.success(next ? '已启用内部销售码平台' : '已关闭内部销售码平台')
  } catch {
    salesEnabled.value = !next  // 回滚开关
    ElMessage.error('操作失败（需要管理员权限）')
  } finally {
    savingSales.value = false
  }
}

/* 外部留言讨论区：运行时开关 + SMTP 配置 */
const discussEnabled = ref(false)
const savingDiscuss = ref(false)
const smtp = ref<SmtpConfig>({ host: '', port: 465, ssl: true, username: '', sender: '', password_set: false })
const smtpPassword = ref('')
const savingSmtp = ref(false)
const smtpTestTo = ref('')
const testingSmtp = ref(false)

async function loadDiscuss() {
  if (!isAdmin.value) return
  try {
    discussEnabled.value = (await settingsApi.getDiscussEnabled()).enabled
    smtp.value = await settingsApi.getSmtp()
  } catch { /* 非管理员/接口故障保持默认 */ }
}

async function onToggleDiscuss(val: string | number | boolean) {
  const next = Boolean(val)
  savingDiscuss.value = true
  try {
    discussEnabled.value = (await settingsApi.setDiscussEnabled(next)).enabled
    await branding.fetchBranding()  // 刷新品牌：侧栏「留言讨论区」菜单即时出现/消失
    ElMessage.success(next ? '已开启留言讨论区' : '已关闭留言讨论区')
  } catch {
    discussEnabled.value = !next
    ElMessage.error('操作失败（需要管理员权限）')
  } finally {
    savingDiscuss.value = false
  }
}

async function saveSmtp() {
  savingSmtp.value = true
  try {
    const payload: Partial<SmtpConfig> & { password?: string } = {
      host: smtp.value.host.trim(), port: smtp.value.port, ssl: smtp.value.ssl,
      username: smtp.value.username.trim(), sender: smtp.value.sender.trim(),
    }
    if (smtpPassword.value.trim()) payload.password = smtpPassword.value.trim()
    smtp.value = await settingsApi.setSmtp(payload)
    smtpPassword.value = ''  // 保存后清空，不回显密码
    ElMessage.success('SMTP 配置已保存')
  } catch {
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    savingSmtp.value = false
  }
}

async function testSmtp() {
  if (!smtpTestTo.value.includes('@')) { ElMessage.warning('请填写测试收件邮箱'); return }
  testingSmtp.value = true
  try {
    // 测试用的是「已保存」配置，故先把当前表单保存下来，保证测试的就是你眼前填的值
    await saveSmtp()
    const r = await settingsApi.testSmtp(smtpTestTo.value.trim())
    if (r.ok) {
      ElMessage.success(r.message)
    } else {
      // 失败原因可能较长（含 SMTP 服务器返回），用带关闭的持久提示，便于阅读排查
      ElMessage({ type: 'error', message: r.message, duration: 8000, showClose: true })
    }
  } catch {
    ElMessage.error('发送失败（需要管理员权限或接口异常）')
  } finally {
    testingSmtp.value = false
  }
}

/* 内部销售码生成二级密码（仅 sales 租户实例） */
const newPwd = ref('')
const confirmPwd = ref('')
const savingPwd = ref(false)
const genPwdIsDefault = ref(true)

async function loadGenPwdStatus() {
  if (!branding.data.sales_code_enabled) return
  try {
    const r = await salesCodeApi.getPwdStatus()
    genPwdIsDefault.value = r.is_default
  } catch {
    // 非管理员/接口故障：保持默认提示
  }
}

async function saveGenPwd() {
  if (newPwd.value.length < 4) { ElMessage.warning('密码至少 4 位'); return }
  if (newPwd.value !== confirmPwd.value) { ElMessage.warning('两次输入不一致'); return }
  savingPwd.value = true
  try {
    const r = await salesCodeApi.setPwd(newPwd.value)
    genPwdIsDefault.value = r.is_default
    newPwd.value = ''
    confirmPwd.value = ''
    ElMessage.success('二级密码已修改')
  } catch {
    ElMessage.error('修改失败（需要管理员权限）')
  } finally {
    savingPwd.value = false
  }
}

/* 飞书机器人应用凭证 */
const feishuAppId = ref('')
const feishuSecret = ref('')
const secretSet = ref(false)
const savingFeishu = ref(false)

async function loadFeishuApp() {
  try {
    const r = await settingsApi.getFeishuApp()
    feishuAppId.value = r.app_id
    secretSet.value = r.secret_set
  } catch {
    // 读取失败（非管理员或接口故障）保持空
  }
}

async function saveFeishuApp() {
  savingFeishu.value = true
  try {
    const payload: { app_id: string; app_secret?: string } = { app_id: feishuAppId.value.trim() }
    if (feishuSecret.value.trim()) payload.app_secret = feishuSecret.value.trim()
    const r = await settingsApi.setFeishuApp(payload)
    feishuAppId.value = r.app_id
    secretSet.value = r.secret_set
    feishuSecret.value = ''  // 保存后清空输入框，不回显密钥
    ElMessage.success('飞书应用配置已保存')
  } catch {
    ElMessage.error('保存失败（需要管理员权限）')
  } finally {
    savingFeishu.value = false
  }
}

/* 数据备份：导出 / 导入 */
const exporting = ref(false)
const importing = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const excelInput = ref<HTMLInputElement | null>(null)
const importingExcel = ref(false)

async function doExport() {
  exporting.value = true
  try {
    const resp = await settingsApi.exportBackup()
    const dispo = (resp.headers['content-disposition'] as string) || ''
    const m = dispo.match(/filename="?([^"]+)"?/)
    const filename = m ? m[1] : `feishu_pm_backup_${Date.now()}.json`
    const url = URL.createObjectURL(resp.data as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('已导出数据快照')
  } catch {
    ElMessage.error('导出失败（需要管理员权限）')
  } finally {
    exporting.value = false
  }
}

function triggerImport() {
  fileInput.value?.click()
}

async function onFileChosen(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    await ElMessageBox.confirm(
      `确定用「${file.name}」全量替换当前数据？此操作将清空并覆盖现有全部数据，不可恢复。`,
      '导入确认',
      { type: 'warning', confirmButtonText: '确定导入', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  importing.value = true
  try {
    const res = await settingsApi.importBackup(file)
    const summary = Object.entries(res.counts).map(([k, v]) => `${k}:${v}`).join('，')
    ElMessage.success(`导入成功（${summary}）`)
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail ? `导入失败：${detail}` : '导入失败（需要管理员权限或文件格式错误）')
  } finally {
    importing.value = false
  }
}

/* 从 Excel 导入项目（周会跟进清单格式）：追加新增，不覆盖现有数据 */
function triggerExcelImport() {
  excelInput.value?.click()
}

async function onExcelChosen(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    await ElMessageBox.confirm(
      `从「${file.name}」导入项目？将按行新增项目（追加导入，不影响现有数据）。`,
      'Excel 导入项目',
      { type: 'warning', confirmButtonText: '开始导入', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  importingExcel.value = true
  try {
    const res = await settingsApi.importProjectsExcel(file)
    if (res.error_count > 0) {
      // 部分失败：列出前若干行错误，便于定位
      const sample = res.errors.slice(0, 8).map((x) => `第 ${x.row} 行：${x.error}`).join('\n')
      const more = res.errors.length > 8 ? `\n…… 等共 ${res.error_count} 行` : ''
      ElMessageBox.alert(
        `成功导入 ${res.created} 个项目，${res.error_count} 行未导入：\n${sample}${more}`,
        '导入完成',
        { type: res.created > 0 ? 'warning' : 'error' },
      )
    } else {
      ElMessage.success(`成功导入 ${res.created} 个项目`)
    }
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail ? `导入失败：${detail}` : '导入失败（文件格式错误或权限不足）')
  } finally {
    importingExcel.value = false
  }
}

onMounted(() => {
  loadFeishuApp()
  loadGenPwdStatus()
  loadSalesEnabled()
  loadDiscuss()
})
</script>

<style scoped>
.other-settings { padding: var(--sp-2) 0; }
.card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-5);
  max-width: 640px;
  margin-bottom: var(--sp-4);
  box-shadow: var(--shadow-sm);
}
.card-title { font-size: 15px; margin-bottom: var(--sp-4); }
.backup-actions { display: flex; align-items: center; gap: var(--sp-3); }
.form-row { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-3); }
.form-row:last-child { margin-bottom: 0; }
.ilabel { width: 80px; flex-shrink: 0; color: var(--c-ink-3); font-size: 13px; }
.hint { font-size: 12px; }
.hint.ok { color: #3DBE7B; }
.hint.warn { color: #E6A23C; }
.tip { margin: var(--sp-3) 0 0; font-size: 12px; line-height: 1.6; }
</style>
