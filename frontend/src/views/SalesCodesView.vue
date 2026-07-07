<template>
  <div class="page">
    <div class="page-head">
      <h1 class="page-title">内部销售码管理</h1>
    </div>

    <el-empty v-if="!isAdmin" description="无权访问（仅管理员）" />

    <el-tabs v-else v-model="activeTab" class="sc-tabs" @tab-change="onTabChange">
      <!-- ============ 生成 ============ -->
      <el-tab-pane label="内部销售码生成" name="generate">
        <section class="card">
          <h3 class="card-title">批量生成</h3>
          <div class="form-row">
            <span class="ilabel">前缀</span>
            <el-select
              v-model="genForm.prefix" placeholder="选择前缀" style="width: 220px" filterable
              no-data-text="前缀库为空，请先到「销售码前缀管理」添加"
            >
              <el-option
                v-for="p in enabledPrefixes" :key="p.id" :label="p.prefix" :value="p.prefix"
              >
                <span>{{ p.prefix }}</span>
                <span class="opt-meta">
                  {{ p.remark || '无备注' }}
                  · {{ p.max_count == null ? '无限制' : `剩 ${p.remaining}/${p.max_count}` }}
                </span>
              </el-option>
            </el-select>
            <span v-if="selectedPrefix" class="muted hint">
              {{ selectedPrefix.remark || '无备注' }}
              · {{ selectedPrefix.max_count == null ? '数量无限制' : `剩余 ${selectedPrefix.remaining} 个` }}
            </span>
          </div>
          <div class="form-row">
            <span class="ilabel">生成数量</span>
            <el-input-number v-model="genForm.count" :min="1" :max="1000" />
          </div>
          <div class="form-row">
            <span class="ilabel">发放对象</span>
            <el-input v-model="genForm.issued_to" placeholder="如：华东渠道 / 张三" style="width: 320px" clearable />
          </div>
          <div class="form-row">
            <span class="ilabel">二级密码</span>
            <el-input v-model="genForm.password" type="password" show-password placeholder="生成二级密码" style="width: 320px" />
          </div>
          <div class="form-row">
            <span class="ilabel"></span>
            <el-button type="primary" :loading="generating" @click="doGenerate">生成</el-button>
            <span class="muted hint">销售码格式：前缀-随机码（如 {{ genForm.prefix || 'ABC' }}-8HKMNP2Q）</span>
          </div>
        </section>

        <section v-if="genResult.length" class="card">
          <div class="card-head">
            <h3 class="card-title">生成结果（{{ genResult.length }} 个）</h3>
            <el-button :icon="Download" @click="exportGenerated">导出 CSV</el-button>
          </div>
          <el-table :data="genResult" size="small" border max-height="420">
            <el-table-column type="index" label="#" width="56" />
            <el-table-column prop="code" label="销售码" min-width="180" />
            <el-table-column prop="issued_to" label="发放对象" min-width="140" />
            <el-table-column label="生成时间" min-width="150">
              <template #default="{ row }">{{ fmt(row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="generated_by" label="生成人" min-width="100" />
          </el-table>
        </section>
      </el-tab-pane>

      <!-- ============ 前缀管理 ============ -->
      <el-tab-pane label="销售码前缀管理" name="prefixes">
        <section class="card">
          <h3 class="card-title">新增前缀</h3>
          <p class="tip muted" style="margin-top:0">前缀为 1~8 位字母或数字（自动转大写），生成销售码时选用形成「前缀-随机码」。</p>
          <div class="form-row">
            <span class="ilabel">前缀</span>
            <el-input
              v-model="prefixForm.prefix" placeholder="≤8 位字母数字" style="width: 220px" maxlength="8"
              @input="prefixForm.prefix = prefixForm.prefix.toUpperCase()"
            />
          </div>
          <div class="form-row">
            <span class="ilabel">备注</span>
            <el-input v-model="prefixForm.remark" placeholder="如：华东渠道专用" style="width: 320px" maxlength="200" clearable />
          </div>
          <div class="form-row">
            <span class="ilabel">数量限制</span>
            <el-input-number v-model="prefixForm.max_count" :min="1" :max="1000000" placeholder="不填=无限制" controls-position="right" />
            <span class="muted hint">留空表示无限制</span>
          </div>
          <div class="form-row">
            <span class="ilabel"></span>
            <el-button type="primary" :loading="addingPrefix" @click="addPrefix">添加到前缀库</el-button>
          </div>
        </section>

        <section class="card">
          <div class="card-head">
            <h3 class="card-title">前缀库（{{ prefixes.length }} 个）</h3>
            <el-button :icon="Refresh" :loading="loadingPrefixes" @click="loadPrefixes">刷新</el-button>
          </div>
          <el-table :data="prefixes" size="small" border max-height="480">
            <el-table-column prop="prefix" label="前缀" min-width="100" />
            <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
            <el-table-column label="数量限制" width="100">
              <template #default="{ row }">{{ row.max_count == null ? '无限制' : row.max_count }}</template>
            </el-table-column>
            <el-table-column label="已生成" width="90">
              <template #default="{ row }">{{ row.used }}</template>
            </el-table-column>
            <el-table-column label="剩余" width="90">
              <template #default="{ row }">{{ row.remaining == null ? '—' : row.remaining }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.disabled ? 'info' : 'success'" size="small">
                  {{ row.disabled ? '已禁用' : '启用中' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_by" label="添加者" min-width="90" />
            <el-table-column label="添加日期" min-width="150">
              <template #default="{ row }">{{ fmt(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="90" fixed="right">
              <template #default="{ row }">
                <el-button
                  size="small" :type="row.disabled ? 'success' : 'warning'" link
                  @click="togglePrefix(row)"
                >
                  {{ row.disabled ? '启用' : '禁用' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>

      <!-- ============ 核销 ============ -->
      <el-tab-pane label="销售码核销" name="redeem">
        <section class="card">
          <h3 class="card-title">逐条核销</h3>
          <div class="form-row">
            <span class="ilabel">销售码</span>
            <el-input
              v-model="singleCode" placeholder="输入单个销售码" style="width: 320px" clearable
              @keyup.enter="doRedeemOne"
            />
            <el-button type="primary" :loading="redeemingOne" @click="doRedeemOne">核销</el-button>
          </div>
        </section>

        <section class="card">
          <h3 class="card-title">批量核销</h3>
          <p class="tip muted" style="margin-top:0">每行一个销售码（也支持逗号/空格分隔）。核销所有可核销的码，失败项在下方列出原因。</p>
          <el-input v-model="batchText" type="textarea" :rows="6" placeholder="ABC-XXXXXXXX&#10;ABC-YYYYYYYY" />
          <div class="form-row" style="margin-top: var(--sp-3)">
            <el-button type="primary" :loading="redeemingBatch" @click="doRedeemBatch">批量核销</el-button>
            <span v-if="batchSummary" class="muted hint">{{ batchSummary }}</span>
          </div>
          <el-table v-if="batchFailed.length" :data="batchFailed" size="small" border style="margin-top: var(--sp-3)">
            <el-table-column prop="code" label="销售码" min-width="180" />
            <el-table-column prop="reason" label="失败原因" min-width="220" />
          </el-table>
        </section>
      </el-tab-pane>

      <!-- ============ 查询 ============ -->
      <el-tab-pane label="销售码查询" name="query">
        <section class="card">
          <h3 class="card-title">查询条件</h3>
          <div class="query-bar">
            <el-input v-model="queryForm.code" placeholder="销售码（模糊）" style="width: 200px" clearable />
            <el-select v-model="queryForm.prefix" placeholder="前缀" clearable filterable style="width: 160px">
              <el-option v-for="p in prefixes" :key="p.id" :label="p.prefix" :value="p.prefix" />
            </el-select>
            <el-date-picker
              v-model="queryForm.range" type="daterange" value-format="YYYY-MM-DD"
              range-separator="至" start-placeholder="生成起" end-placeholder="生成止" style="width: 250px"
            />
            <el-select v-model="queryForm.redeemed" placeholder="核销状态" clearable style="width: 130px">
              <el-option label="全部" :value="undefined" />
              <el-option label="未核销" :value="false" />
              <el-option label="已核销" :value="true" />
            </el-select>
            <el-button type="primary" :loading="querying" @click="doQuery">查询</el-button>
          </div>
        </section>

        <section class="card">
          <div class="card-head">
            <h3 class="card-title">查询结果（{{ queryResult.length }} 条）</h3>
            <el-button :icon="Download" :disabled="!queryResult.length" @click="exportQuery">导出 CSV</el-button>
          </div>
          <el-table :data="queryResult" size="small" border max-height="520">
            <el-table-column prop="code" label="销售码" min-width="170" fixed />
            <el-table-column prop="prefix" label="前缀" width="90" />
            <el-table-column prop="issued_to" label="发放对象" min-width="130" />
            <el-table-column label="生成时间" min-width="150">
              <template #default="{ row }">{{ fmt(row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="generated_by" label="生成人" min-width="90" />
            <el-table-column label="是否核销" width="90">
              <template #default="{ row }">
                <el-tag :type="row.redeemed ? 'success' : 'info'" size="small">
                  {{ row.redeemed ? '已核销' : '未核销' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="核销时间" min-width="150">
              <template #default="{ row }">{{ fmt(row.redeemed_at) }}</template>
            </el-table-column>
            <el-table-column prop="redeemed_by" label="核销人" min-width="90" />
          </el-table>
        </section>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Refresh } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { salesCodeApi } from '@/api/resources'
import type { SalesCode, SalesCodePrefix } from '@/types'

const auth = useAuthStore()
const isAdmin = computed(() => auth.currentUser?.role === 'admin')
const activeTab = ref('generate')

/* 生成时间等 ISO 串 → 「YYYY-MM-DD HH:mm」（后端为本地朴素时间，直接截取不做时区换算） */
function fmt(s?: string | null): string {
  return s ? s.replace('T', ' ').slice(0, 16) : ''
}

/* 导出文件名时间戳：YYYYMMDDHHmm（本地时间） */
function nowStamp(): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}${p(d.getHours())}${p(d.getMinutes())}`
}

/* ---------- 前缀库 ---------- */
const prefixes = ref<SalesCodePrefix[]>([])
const loadingPrefixes = ref(false)
const enabledPrefixes = computed(() => prefixes.value.filter((p) => !p.disabled))
const selectedPrefix = computed(() => prefixes.value.find((p) => p.prefix === genForm.prefix) || null)

async function loadPrefixes() {
  loadingPrefixes.value = true
  try {
    prefixes.value = await salesCodeApi.listPrefixes()
  } catch {
    ElMessage.error('加载前缀库失败（需要管理员权限）')
  } finally {
    loadingPrefixes.value = false
  }
}

const prefixForm = reactive<{ prefix: string; remark: string; max_count: number | undefined }>({
  prefix: '', remark: '', max_count: undefined,
})
const addingPrefix = ref(false)

async function addPrefix() {
  const prefix = prefixForm.prefix.trim().toUpperCase()
  if (!/^[A-Z0-9]{1,8}$/.test(prefix)) { ElMessage.warning('前缀需为 1~8 位字母或数字'); return }
  addingPrefix.value = true
  try {
    await salesCodeApi.createPrefix({
      prefix, remark: prefixForm.remark.trim(),
      max_count: prefixForm.max_count ?? null,
    })
    ElMessage.success(`已添加前缀 ${prefix}`)
    prefixForm.prefix = ''
    prefixForm.remark = ''
    prefixForm.max_count = undefined
    await loadPrefixes()
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '添加失败')
  } finally {
    addingPrefix.value = false
  }
}

async function togglePrefix(row: SalesCodePrefix) {
  try {
    await salesCodeApi.setPrefixDisabled(row.id, !row.disabled)
    ElMessage.success(row.disabled ? `已启用 ${row.prefix}` : `已禁用 ${row.prefix}`)
    await loadPrefixes()
  } catch {
    ElMessage.error('操作失败（需要管理员权限）')
  }
}

/* ---------- 生成 ---------- */
const genForm = reactive({ prefix: '', count: 10, issued_to: '', password: '' })
const generating = ref(false)
const genResult = ref<SalesCode[]>([])

async function doGenerate() {
  if (!genForm.prefix) { ElMessage.warning('请选择前缀'); return }
  if (!genForm.issued_to.trim()) { ElMessage.warning('请填写发放对象'); return }
  if (!genForm.password) { ElMessage.warning('请输入二级密码'); return }
  try {
    await ElMessageBox.confirm(
      `将以前缀「${genForm.prefix}」生成 ${genForm.count} 个销售码，发放对象：${genForm.issued_to.trim()}。确认生成？`,
      '确认生成', { type: 'warning', confirmButtonText: '确认生成', cancelButtonText: '取消' },
    )
  } catch { return }
  generating.value = true
  try {
    genResult.value = await salesCodeApi.generate({
      count: genForm.count, prefix: genForm.prefix,
      issued_to: genForm.issued_to.trim(), password: genForm.password,
    })
    genForm.password = ''  // 生成后清空密码，不残留
    ElMessage.success(`已生成 ${genResult.value.length} 个销售码`)
    await loadPrefixes()   // 刷新剩余量
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail || '生成失败')
  } finally {
    generating.value = false
  }
}

/* CSV 导出：带 UTF-8 BOM（Excel 中文不乱码），字段按需转义 */
function csvCell(v: unknown): string {
  const s = String(v ?? '')
  return /[",\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s
}
function exportGenerated() {
  const header = ['销售码', '发放对象', '生成时间', '生成人']
  const rows = genResult.value.map((r) => [r.code, r.issued_to, fmt(r.created_at), r.generated_by])
  const csv = '﻿' + [header, ...rows].map((cols) => cols.map(csvCell).join(',')).join('\r\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `sales_codes_${nowStamp()}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

/* ---------- 核销 ---------- */
const singleCode = ref('')
const redeemingOne = ref(false)

async function doRedeemOne() {
  const code = singleCode.value.trim()
  if (!code) { ElMessage.warning('请输入销售码'); return }
  redeemingOne.value = true
  try {
    const res = await salesCodeApi.redeem(code)
    if (res.ok) {
      ElMessage.success(`核销成功：${code}`)
      singleCode.value = ''
    } else {
      ElMessage.error(`核销失败：${res.reason}`)
    }
  } catch {
    ElMessage.error('核销失败（需要管理员权限）')
  } finally {
    redeemingOne.value = false
  }
}

const batchText = ref('')
const redeemingBatch = ref(false)
const batchSummary = ref('')
const batchFailed = ref<{ code: string; reason: string }[]>([])

async function doRedeemBatch() {
  const codes = batchText.value.split(/[\s,，]+/).map((s) => s.trim()).filter(Boolean)
  if (!codes.length) { ElMessage.warning('请输入至少一个销售码'); return }
  redeemingBatch.value = true
  try {
    const res = await salesCodeApi.redeemBatch(codes)
    batchFailed.value = res.failed
    batchSummary.value = `成功核销 ${res.redeemed.length} 个，失败 ${res.failed.length} 个`
    if (res.failed.length === 0) ElMessage.success(batchSummary.value)
    else ElMessage.warning(batchSummary.value)
  } catch {
    ElMessage.error('核销失败（需要管理员权限）')
  } finally {
    redeemingBatch.value = false
  }
}

/* ---------- 查询 ---------- */
const queryForm = reactive<{ code: string; prefix: string; range: [string, string] | null; redeemed: boolean | undefined }>({
  code: '', prefix: '', range: null, redeemed: undefined,
})
const querying = ref(false)
const queryResult = ref<SalesCode[]>([])

async function doQuery() {
  querying.value = true
  try {
    queryResult.value = await salesCodeApi.query({
      code: queryForm.code.trim() || undefined,
      prefix: queryForm.prefix || undefined,
      start: queryForm.range?.[0] || undefined,
      end: queryForm.range?.[1] || undefined,
      redeemed: queryForm.redeemed,
    })
    if (!queryResult.value.length) ElMessage.info('无匹配记录')
  } catch {
    ElMessage.error('查询失败（需要管理员权限）')
  } finally {
    querying.value = false
  }
}

/* 查询结果导出 CSV：复用 csvCell 转义 + UTF-8 BOM（Excel 中文不乱码） */
function exportQuery() {
  if (!queryResult.value.length) return
  const header = ['销售码', '前缀', '发放对象', '生成时间', '生成人', '是否核销', '核销时间', '核销人']
  const rows = queryResult.value.map((r) => [
    r.code, r.prefix, r.issued_to, fmt(r.created_at), r.generated_by,
    r.redeemed ? '已核销' : '未核销', fmt(r.redeemed_at), r.redeemed_by ?? '',
  ])
  const csv = '﻿' + [header, ...rows].map((cols) => cols.map(csvCell).join(',')).join('\r\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `sales_codes_query_${nowStamp()}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

/* 首次进入即加载前缀库（生成下拉/查询下拉都要用）；切到相关页也刷新一次 */
function onTabChange(name: string) {
  if (name === 'generate' || name === 'prefixes' || name === 'query') loadPrefixes()
}
onMounted(() => { if (isAdmin.value) loadPrefixes() })
</script>

<style scoped>
.page { padding: var(--sp-6); }
.page-head { margin-bottom: var(--sp-2); }
.page-title { font-family: var(--font-display); font-size: 22px; font-weight: 700; }
.sc-tabs { margin-top: var(--sp-4); }
.card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-5);
  max-width: 900px;
  margin-bottom: var(--sp-4);
  box-shadow: var(--shadow-sm);
}
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--sp-4); }
.card-head .card-title { margin-bottom: 0; }
.card-title { font-size: 15px; margin-bottom: var(--sp-4); }
.form-row { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-3); }
.form-row:last-child { margin-bottom: 0; }
.ilabel { width: 72px; flex-shrink: 0; color: var(--c-ink-3); font-size: 13px; }
.query-bar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sp-3); }
.tip { margin: var(--sp-3) 0; font-size: 12px; line-height: 1.6; }
.hint { font-size: 12px; }
.opt-meta { margin-left: var(--sp-3); color: var(--c-ink-3); font-size: 12px; }
:deep(.el-tabs__item.is-active) { color: var(--c-accent); }
:deep(.el-tabs__nav-wrap::after) { background-color: var(--c-border); }
</style>
