<template>
  <div class="page discuss-admin">
    <div class="page-head">
      <h1 class="page-title">留言讨论区</h1>
      <a class="da-open-link" href="/forum" target="_blank">打开公开留言页 ↗</a>
    </div>

    <!-- 筛选工具条 -->
    <div class="da-toolbar">
      <el-input v-model="keyword" placeholder="搜索 内容 / 昵称 / 邮箱 / 手机号" clearable
        style="width: 300px" @keyup.enter="load" />
      <el-checkbox v-model="onlyUnreplied" @change="load">仅看未回复</el-checkbox>
      <el-select v-model="minStar" style="width: 140px" @change="load">
        <el-option :value="0" label="全部星级" />
        <el-option v-for="s in 5" :key="s" :value="s" :label="'★'.repeat(s) + ' 及以上'" />
      </el-select>
      <el-button type="primary" :loading="loading" @click="load">查询</el-button>
      <span class="muted">共 {{ total }} 楼</span>
    </div>

    <!-- 楼列表 -->
    <div v-loading="loading" class="da-list">
      <div v-for="t in threads" :key="t.id" class="da-thread" :class="{ hidden: t.status === 'hidden' }">
        <div class="da-head">
          <span class="da-author">{{ t.author_name }}</span>
          <span v-if="!t.replied" class="da-unreplied">未回复</span>
          <span v-if="t.status === 'hidden'" class="da-hidden-tag">已隐藏</span>
          <span class="da-contact muted">{{ t.ext_email }} · {{ t.ext_phone }}</span>
          <span class="da-time muted">{{ t.created_at }}</span>
        </div>
        <p class="da-content">{{ t.content }}</p>
        <!-- 附件 -->
        <div v-if="t.attachments?.length" class="da-media">
          <template v-for="a in t.attachments" :key="a.url">
            <img v-if="a.type === 'image'" :src="a.url" class="da-img" alt="" @click="zoomSrc = a.url" />
            <video v-else :src="a.url" class="da-video" controls preload="metadata" />
          </template>
        </div>
        <!-- 楼内回复 -->
        <div v-for="r in t.replies" :key="r.id" class="da-reply" :class="{ official: r.author_type === 'internal' }">
          <b>{{ r.author_name }}</b>
          <span v-if="r.author_type === 'internal'" class="da-badge">官方</span>
          <span class="muted da-time">{{ r.created_at }}</span>
          <p class="da-content">{{ r.content }}</p>
        </div>
        <!-- 操作行：星级 + 回复 + 隐藏 + 封禁 -->
        <div class="da-actions">
          <el-rate :model-value="t.star" :max="5" clearable
            @change="(v: number) => setStar(t, v)" />
          <el-button size="small" type="primary" plain @click="replyFor = replyFor === t.id ? null : t.id">回复</el-button>
          <el-button size="small" plain @click="toggleVisible(t)">{{ t.status === 'hidden' ? '恢复显示' : '隐藏' }}</el-button>
          <el-button size="small" :type="t.ext_blocked ? 'success' : 'danger'" plain @click="toggleBlock(t)">
            {{ t.ext_blocked ? '解封用户' : '封禁用户' }}
          </el-button>
        </div>
        <div v-if="replyFor === t.id" class="da-reply-box">
          <el-input v-model="replyDraft" type="textarea" :rows="2" maxlength="2000" placeholder="回复内容…" />
          <el-button type="primary" size="small" :loading="replying" style="margin-top:6px"
            @click="submitReply(t.id)">发送回复</el-button>
        </div>
      </div>
      <el-empty v-if="!threads.length && !loading" description="暂无留言" />
      <el-pagination v-if="total > size" layout="prev, pager, next" :total="total" :page-size="size"
        :current-page="page" @current-change="(p: number) => { page = p; load() }" style="margin-top: 12px" />
    </div>

    <!-- 图片放大遮罩：根级单例，点击任意处关闭 -->
    <div v-if="zoomSrc" class="da-zoom" @click="zoomSrc = null">
      <img :src="zoomSrc" class="da-zoom-img" alt="" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { discussApi } from '@/api/resources'
import type { DiscussMessage } from '@/types'

const threads = ref<DiscussMessage[]>([])
const total = ref(0)
const page = ref(1)
const size = 10
const loading = ref(false)
const keyword = ref('')
const onlyUnreplied = ref(false)
const minStar = ref(0)

const replyFor = ref<number | null>(null)
const replyDraft = ref('')
const replying = ref(false)
const zoomSrc = ref<string | null>(null)   // 图片放大遮罩

onMounted(load)

async function load() {
  loading.value = true
  try {
    const r = await discussApi.adminThreads({
      page: page.value, size, keyword: keyword.value.trim(),
      only_unreplied: onlyUnreplied.value, min_star: minStar.value,
    })
    threads.value = r.items
    total.value = r.total
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function submitReply(threadId: number) {
  if (!replyDraft.value.trim()) return
  replying.value = true
  try {
    await discussApi.adminReply(threadId, replyDraft.value.trim())
    replyDraft.value = ''
    replyFor.value = null
    ElMessage.success('已回复')
    await load()
  } catch {
    ElMessage.error('回复失败')
  } finally {
    replying.value = false
  }
}

async function setStar(t: DiscussMessage, star: number) {
  const next = star ?? 0
  if (next === (t.star ?? 0)) return   // 无变化（含初始/重复触发）不调接口、不弹提示
  try {
    const r = await discussApi.adminStar(t.id, next)
    t.star = r.star
    ElMessage.success(r.star > 0 ? `已评 ${r.star} 星` : '已取消星级')
  } catch {
    ElMessage.error('操作失败')
  }
}

async function toggleVisible(t: DiscussMessage) {
  try {
    const r = await discussApi.adminVisibility(t.id, t.status === 'hidden')
    t.status = r.status
  } catch {
    ElMessage.error('操作失败')
  }
}

async function toggleBlock(t: DiscussMessage) {
  if (!t.ext_user_id) return
  const blocking = !t.ext_blocked
  if (blocking) {
    try {
      await ElMessageBox.confirm(`确定封禁用户「${t.author_name}」？封禁后其不能再登录和发言。`, '封禁确认',
        { type: 'warning', confirmButtonText: '封禁', cancelButtonText: '取消' })
    } catch { return }
  }
  try {
    await discussApi.adminBlock(t.ext_user_id, blocking)
    t.ext_blocked = blocking
    ElMessage.success(blocking ? '已封禁' : '已解封')
  } catch {
    ElMessage.error('操作失败')
  }
}
</script>

<style scoped>
.discuss-admin { padding: var(--sp-5); }
.page-head { display: flex; align-items: baseline; gap: var(--sp-4); margin-bottom: var(--sp-4); }
.da-open-link { font-size: 13px; color: var(--c-accent); text-decoration: none; }
.da-toolbar { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-4); flex-wrap: wrap; }
.da-list { display: flex; flex-direction: column; gap: var(--sp-3); }
.da-thread { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--r-md);
  padding: var(--sp-4); }
.da-thread.hidden { opacity: .55; }
.da-head { display: flex; align-items: baseline; gap: var(--sp-2); flex-wrap: wrap; margin-bottom: 4px; }
.da-author { font-weight: 700; }
.da-unreplied { background: #fdf3c4; color: #9b6a00; font-size: 11px; padding: 1px 8px; border-radius: 999px; font-weight: 600; }
.da-hidden-tag { background: var(--c-surface-2); color: var(--c-ink-3); font-size: 11px; padding: 1px 8px; border-radius: 999px; }
.da-contact { font-size: 12px; }
.da-time { font-size: 12px; margin-left: auto; }
.da-content { margin: 4px 0; font-size: 14px; line-height: 1.7; white-space: pre-wrap; word-break: break-word; }
.da-media { display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0; }
.da-img { max-height: 140px; border-radius: 8px; cursor: zoom-in; }
.da-video { max-height: 200px; max-width: 320px; border-radius: 8px; background: #000; }
.da-reply { margin-top: 8px; padding: 8px 12px; background: var(--c-surface-2); border-radius: 8px; font-size: 13px; }
.da-reply.official { background: var(--c-accent-soft); }
.da-badge { background: var(--c-accent); color: #fff; font-size: 11px; padding: 0 7px; border-radius: 999px; margin-left: 6px; }
.da-actions { display: flex; align-items: center; gap: var(--sp-3); margin-top: var(--sp-3); flex-wrap: wrap; }
.da-reply-box { margin-top: var(--sp-2); }
.da-zoom { position: fixed; inset: 0; background: rgba(0,0,0,.85); z-index: 3000;
  display: flex; align-items: center; justify-content: center; cursor: zoom-out; }
.da-zoom-img { max-width: 96vw; max-height: 92vh; object-fit: contain; }
</style>
