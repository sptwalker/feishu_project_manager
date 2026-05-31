<template>
  <div class="page">
    <!-- 头部 -->
    <div class="thead">
      <div class="crumbs">
        <span class="link" @click="$router.push({ name: 'board' })">项目看板</span>
        <span class="sep">/</span>
        <span class="cur">{{ project?.name || '加载中…' }}</span>
      </div>
      <div class="head-actions">
        <el-button type="primary" :icon="Plus" @click="openCreate">新建风险</el-button>
      </div>
    </div>

    <!-- 任务 / 风险 切换 -->
    <div class="tabrow">
      <ProjectTabs :project-id="projectId" />
      <div class="risk-summary muted">
        <span><b class="num">{{ countBy('open') }}</b> 未关闭</span>
        <span><b class="num">{{ countBy('monitoring') }}</b> 监控中</span>
        <span><b class="num">{{ countBy('resolved') }}</b> 已解决</span>
      </div>
    </div>

    <!-- 风险按状态分列 -->
    <div v-loading="loading" class="cols">
      <section v-for="col in RISK_STATUS_ORDER" :key="col" class="rcol">
        <header class="rcol-head" :style="{ '--dot': statusColor(col) }">
          <span class="rdot" />
          <span class="rcol-title">{{ statusLabel(col) }}</span>
          <span class="rcol-count num">{{ grouped[col]?.length || 0 }}</span>
        </header>
        <div class="rcol-body">
          <article
            v-for="r in grouped[col]"
            :key="r.id"
            class="rcard"
            :style="{ background: statusSoft(col) }"
            @click="openEdit(r)"
          >
            <h4 class="rtitle">{{ r.title }}</h4>
            <p v-if="r.description" class="rdesc">{{ r.description }}</p>
            <div class="rmeta muted">
              <span :style="{ color: statusColor(col) }">{{ statusLabel(col) }}</span>
              <span v-if="r.owner_name">· 负责人 {{ r.owner_name }}</span>
            </div>
          </article>
          <el-empty v-if="!loading && !(grouped[col]?.length)" :image-size="0" description="—" />
        </div>
      </section>
    </div>

    <!-- 风险创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑风险' : '新建风险'" width="480px">
      <el-form :model="form" label-width="84px" label-position="left">
        <el-form-item label="风险标题" required>
          <el-input v-model="form.title" placeholder="请输入风险标题" />
        </el-form-item>
        <el-form-item label="风险描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="s in RISK_STATUS_ORDER" :key="s" :label="statusLabel(s)" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="form.owner_name" style="width: 100%" placeholder="负责人姓名（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button v-if="editing" type="danger" plain style="float: left" @click="remove">删除</el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { projectApi, riskApi } from '@/api/resources'
import type { Project, Risk, RiskStatus } from '@/types'
import {
  riskStatusLabel, riskStatusColor, riskStatusSoft, RISK_STATUS_ORDER,
} from '@/utils/labels'
import ProjectTabs from '@/components/ProjectTabs.vue'

const props = defineProps<{ id: string }>()
const projectId = computed(() => Number(props.id))

const project = ref<Project | null>(null)
const risks = ref<Risk[]>([])
const loading = ref(false)

const statusLabel = (s: RiskStatus) => riskStatusLabel[s]
const statusColor = (s: RiskStatus) => riskStatusColor[s]
const statusSoft = (s: RiskStatus) => riskStatusSoft[s]

const grouped = computed<Record<RiskStatus, Risk[]>>(() => {
  const g: Record<RiskStatus, Risk[]> = { open: [], monitoring: [], resolved: [] }
  for (const r of risks.value) g[r.status]?.push(r)
  return g
})
const countBy = (s: RiskStatus) => risks.value.filter((r) => r.status === s).length

async function load() {
  loading.value = true
  try {
    const [p, rs] = await Promise.all([
      projectApi.get(projectId.value),
      riskApi.listByProject(projectId.value, { limit: 100 }),
    ])
    project.value = p
    risks.value = rs
  } catch {
    ElMessage.error('加载风险失败')
  } finally {
    loading.value = false
  }
}

/* 创建 / 编辑 */
const dialogVisible = ref(false)
const editing = ref<Risk | null>(null)
const saving = ref(false)
const form = reactive<Record<string, unknown>>({
  title: '', description: '', status: 'open', owner_name: '',
})

function openCreate() {
  editing.value = null
  Object.assign(form, { title: '', description: '', status: 'open', owner_name: '' })
  dialogVisible.value = true
}

function openEdit(r: Risk) {
  editing.value = r
  Object.assign(form, {
    title: r.title, description: r.description ?? '', status: r.status, owner_name: r.owner_name ?? '',
  })
  dialogVisible.value = true
}

async function submit() {
  if (!form.title) {
    ElMessage.warning('请填写风险标题')
    return
  }
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...form }
    if (!payload.description) delete payload.description
    if (!payload.owner_name) delete payload.owner_name
    if (editing.value) {
      await riskApi.update(editing.value.id, payload as Partial<Risk>)
      ElMessage.success('风险已更新')
    } else {
      await riskApi.create(projectId.value, payload as Partial<Risk>)
      ElMessage.success('风险已创建')
    }
    dialogVisible.value = false
    await load()
  } catch {
    ElMessage.error('保存失败（请检查负责人ID或权限）')
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!editing.value) return
  try {
    await ElMessageBox.confirm('确定删除该风险？', '删除确认', { type: 'warning' })
  } catch {
    return
  }
  try {
    await riskApi.remove(editing.value.id)
    ElMessage.success('已删除')
    dialogVisible.value = false
    await load()
  } catch {
    ElMessage.error('删除失败（可能无权限）')
  }
}

onMounted(load)
</script>

<style scoped>
.thead {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--sp-4); flex-wrap: wrap; gap: var(--sp-3);
}
.crumbs { font-family: var(--font-display); font-size: 18px; font-weight: 600; }
.link { color: var(--c-ink-3); cursor: pointer; }
.link:hover { color: var(--c-accent); }
.sep { color: var(--c-ink-3); margin: 0 var(--sp-2); }
.cur { color: var(--c-ink); }

.tabrow {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--sp-4); gap: var(--sp-4); flex-wrap: wrap;
}
.risk-summary { display: flex; gap: var(--sp-5); font-size: 14px; }
.risk-summary b { color: var(--c-ink); margin-right: 4px; }

.cols {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--sp-4); align-items: start;
}
@media (max-width: 860px) { .cols { grid-template-columns: 1fr; } }
.rcol {
  background: var(--c-surface-2);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: var(--sp-3);
  min-height: 120px;
}
.rcol-head { display: flex; align-items: center; gap: var(--sp-2); padding: var(--sp-1) var(--sp-2) var(--sp-3); }
.rdot { width: 8px; height: 8px; border-radius: 50%; background: var(--dot); }
.rcol-title { font-family: var(--font-display); font-weight: 600; font-size: 14px; }
.rcol-count { margin-left: auto; color: var(--c-ink-3); font-size: 13px; font-weight: 600; }
.rcol-body { display: flex; flex-direction: column; gap: var(--sp-2); }

.rcard {
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  padding: var(--sp-3);
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.1s;
}
.rcard:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.rtitle { font-size: 14px; font-weight: 600; margin-bottom: var(--sp-1); }
.rdesc {
  font-size: 13px; color: var(--c-ink-2); margin: 0 0 var(--sp-2);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.rmeta { font-size: 12px; display: flex; gap: var(--sp-2); }
</style>
