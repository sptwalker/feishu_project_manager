<template>
  <div class="forum">
    <!-- 顶部：标题 + 登录态 -->
    <header class="fm-head">
      <div class="fm-title-row">
        <h1 class="fm-title">{{ board?.title || '用户留言区' }}</h1>
        <div class="fm-user">
          <template v-if="me">
            <span class="fm-nick">{{ me.nickname }}</span>
            <button class="fm-link-btn" @click="logout">退出</button>
          </template>
          <button v-else class="fm-link-btn" @click="authVisible = true">登录 / 注册</button>
        </div>
      </div>
      <p v-if="board?.welcome_text" class="fm-welcome">{{ board.welcome_text }}</p>
    </header>

    <!-- 讨论区关闭态 -->
    <div v-if="board && !board.enabled" class="fm-closed">留言区暂未开放，请稍后再来。</div>

    <template v-else-if="board">
      <!-- 公告区（Markdown 渲染；PMS 管理员可编辑，其余用户只读） -->
      <section v-if="announcementHtml || canEditAnnouncement" class="fm-announce">
        <div class="fm-announce-head">
          <span class="fm-announce-title">📢 公告</span>
          <button v-if="canEditAnnouncement" class="fm-link-btn" @click="openAnnounceEdit">编辑</button>
        </div>
        <!-- 公告为管理员录入的可信内容，marked 渲染后 v-html 展示 -->
        <div v-if="announcementHtml" class="fm-md" v-html="announcementHtml"></div>
        <div v-else class="fm-announce-empty">暂无公告，点击「编辑」添加。</div>
      </section>

      <!-- 发留言入口 -->
      <section class="fm-composer">
        <textarea v-model="draft" class="fm-input" rows="3"
          :placeholder="me ? '写下你的留言…（支持图片 / 视频）' : '登录后即可留言'"
          :disabled="!me" maxlength="2000"></textarea>
        <!-- 已选附件预览 -->
        <div v-if="draftAtts.length" class="fm-att-list">
          <div v-for="(a, i) in draftAtts" :key="a.url" class="fm-att-item">
            <img v-if="a.type === 'image'" :src="a.url" class="fm-att-thumb" alt="" @click="zoomSrc = a.url" />
            <span v-else class="fm-att-video">🎬 {{ a.name }}</span>
            <button class="fm-att-del" @click="draftAtts.splice(i, 1)">✕</button>
          </div>
        </div>
        <div class="fm-composer-bar">
          <div class="fm-tools">
            <button class="fm-tool-btn" :disabled="!me || uploading || imgCount >= MAX_IMAGES" @click="pickFile('image/jpeg,image/png')">📷 图片</button>
            <button class="fm-tool-btn" :disabled="!me || uploading || vidCount >= MAX_VIDEOS" @click="pickFile('video/*')">🎬 视频</button>
            <span v-if="uploading" class="fm-uploading">上传中…</span>
            <span v-else-if="me && draftAtts.length" class="fm-uploading">图片 {{ imgCount }}/{{ MAX_IMAGES }} · 视频 {{ vidCount }}/{{ MAX_VIDEOS }}</span>
          </div>
          <button class="fm-send" :disabled="!me || sending || !draft.trim()" @click="submitRoot">发布</button>
        </div>
        <input ref="fileInput" type="file" style="display:none" @change="onFile" />
      </section>

      <!-- 留言列表（楼）：仅登录后显示，且只含本人的留言 + 官方回复 -->
      <section v-if="me" class="fm-list" v-loading="loading">
        <p class="fm-mine-tip">这里只显示你自己的留言与官方回复，其他用户看不到你的内容。</p>
        <article v-for="t in threads" :key="t.id" class="fm-thread">
          <div class="fm-msg">
            <div class="fm-msg-head">
              <span class="fm-author">{{ t.author_name }}</span>
              <span v-if="t.star > 0" class="fm-star" title="官方评价">{{ '★'.repeat(t.star) }}</span>
              <span class="fm-time">{{ t.created_at }}</span>
            </div>
            <!-- 外部内容永远纯文本渲染（{{}} 插值），绝不 v-html -->
            <p class="fm-content">{{ t.content }}</p>
            <div v-if="t.attachments && t.attachments.length" class="fm-media">
              <template v-for="(a, i) in t.attachments" :key="i">
                <img v-if="a.type === 'image'" class="fm-media-img" :src="a.url" :alt="a.name" loading="lazy" @click="zoomSrc = a.url" />
                <video v-else class="fm-media-video" :src="a.url" controls preload="metadata"></video>
              </template>
            </div>
          </div>
          <!-- 楼内回复 -->
          <div v-for="r in t.replies" :key="r.id" class="fm-reply" :class="{ official: r.author_type === 'internal' }">
            <div class="fm-msg-head">
              <span class="fm-author">{{ r.author_name }}</span>
              <span v-if="r.author_type === 'internal'" class="fm-badge">官方</span>
              <span class="fm-time">{{ r.created_at }}</span>
            </div>
            <p class="fm-content">{{ r.content }}</p>
            <div v-if="r.attachments && r.attachments.length" class="fm-media">
              <template v-for="(a, i) in r.attachments" :key="i">
                <img v-if="a.type === 'image'" class="fm-media-img" :src="a.url" :alt="a.name" loading="lazy" @click="zoomSrc = a.url" />
                <video v-else class="fm-media-video" :src="a.url" controls preload="metadata"></video>
              </template>
            </div>
          </div>
          <!-- 本人楼内补充 -->
          <div v-if="me && t.author_name === me.nickname" class="fm-append">
            <template v-if="appendFor === t.id">
              <textarea v-model="appendDraft" class="fm-input" rows="2" placeholder="补充内容…" maxlength="2000"></textarea>
              <div class="fm-composer-bar">
                <button class="fm-link-btn" @click="appendFor = null">取消</button>
                <button class="fm-send" :disabled="sending || !appendDraft.trim()" @click="submitAppend(t.id)">提交</button>
              </div>
            </template>
            <button v-else class="fm-link-btn" @click="appendFor = t.id; appendDraft = ''">＋ 补充留言</button>
          </div>
        </article>
        <div v-if="!threads.length && !loading" class="fm-empty">你还没有留言，在上方写下第一条吧。</div>
        <button v-if="threads.length < total" class="fm-more" :disabled="loading" @click="loadMore">加载更多</button>
      </section>
      <!-- 未登录：不展示任何留言（用户只能看到自己的内容） -->
      <section v-else class="fm-list">
        <div class="fm-empty">登录后即可查看并管理你的留言。</div>
      </section>
    </template>

    <!-- 登录 / 注册弹层（底部抽屉式，移动端友好） -->
    <div v-if="authVisible" class="fm-mask" @click.self="authVisible = false">
      <div class="fm-sheet">
        <div class="fm-sheet-head">
          <button class="fm-tab" :class="{ on: authMode === 'login' }" @click="authMode = 'login'">登录</button>
          <button class="fm-tab" :class="{ on: authMode === 'register' }" @click="authMode = 'register'">注册</button>
          <button class="fm-sheet-close" @click="authVisible = false">✕</button>
        </div>
        <div class="fm-form">
          <input v-model="authEmail" class="fm-field" type="email" placeholder="邮箱" maxlength="200" />
          <div class="fm-code-row">
            <input v-model="authCode" class="fm-field" placeholder="验证码" maxlength="6" />
            <button class="fm-code-btn" :disabled="codeCooldown > 0 || !authEmail.includes('@')" @click="sendCode">
              {{ codeCooldown > 0 ? `${codeCooldown}s` : '获取验证码' }}
            </button>
          </div>
          <template v-if="authMode === 'register'">
            <input v-model="authNickname" class="fm-field" placeholder="昵称（公开显示）" maxlength="50" />
            <input v-model="authPhone" class="fm-field" type="tel" placeholder="手机号" maxlength="30" />
          </template>
          <button class="fm-send fm-auth-submit" :disabled="authing" @click="doAuth">
            {{ authing ? '处理中…' : authMode === 'login' ? '登录' : '注册并登录' }}
          </button>
          <p v-if="authError" class="fm-error">{{ authError }}</p>
        </div>
      </div>
    </div>
    <!-- 编辑公告弹层（仅 PMS 管理员）：Markdown 录入 + 实时预览 -->
    <div v-if="announceEditVisible" class="fm-mask" @click.self="announceEditVisible = false">
      <div class="fm-sheet fm-announce-sheet">
        <div class="fm-sheet-head">
          <span class="fm-sheet-title">编辑公告（支持 Markdown）</span>
          <button class="fm-sheet-close" @click="announceEditVisible = false">✕</button>
        </div>
        <textarea v-model="announceDraft" class="fm-announce-input"
          placeholder="支持 Markdown：# 标题、**加粗**、- 列表、[链接](https://…)、`代码` 等"></textarea>
        <div class="fm-announce-preview-label">预览</div>
        <div class="fm-md fm-announce-preview" v-html="draftHtml"></div>
        <div class="fm-announce-actions">
          <button class="fm-link-btn" @click="announceEditVisible = false">取消</button>
          <button class="fm-send" :disabled="savingAnnounce" @click="saveAnnounce">
            {{ savingAnnounce ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>
    <!-- 图片放大遮罩：根级单例，点击任意处关闭 -->
    <div v-if="zoomSrc" class="fm-zoom" @click="zoomSrc = null">
      <img :src="zoomSrc" class="fm-zoom-img" alt="" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { discussApi, discussTokenStore } from '@/api/resources'
import type { DiscussBoardInfo, DiscussMessage, DiscussAttachment } from '@/types'

// 单帖附件数量上限（与后端 discuss/service.py 保持一致，防刷图/刷视频）
const MAX_IMAGES = 9
const MAX_VIDEOS = 1

// 图片放大：单一根级遮罩（避免嵌在消息树里被祖先裁剪/层叠影响），composer 预览与已发消息共用
const zoomSrc = ref<string | null>(null)

const board = ref<DiscussBoardInfo | null>(null)
const threads = ref<DiscussMessage[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)

/* 外部登录态：token 存 dsc_token，昵称/邮箱缓存本地便于显示 */
const me = ref<{ nickname: string; email: string } | null>(null)

/* 公告：markdown 源文存于 board.announcement，marked 渲染展示。
   编辑权限判定：同浏览器已登录内部系统且持有留言区「公告」权限（不触发登录跳转）。 */
const canEditAnnouncement = ref(false)
const announceEditVisible = ref(false)
const announceDraft = ref('')
const savingAnnounce = ref(false)
const announcementHtml = computed(() => (board.value?.announcement ? renderMd(board.value.announcement) : ''))
const draftHtml = computed(() => (announceDraft.value ? renderMd(announceDraft.value) : '<span style="color:#8a8a94">（空）</span>'))

/* Markdown → HTML → 白名单消毒：即便管理员账号被盗写入带脚本的公告，
   DOMPurify 也会剔除 <script>/onerror/javascript: 等危险内容，只保留安全排版标签。 */
function renderMd(src: string): string {
  return DOMPurify.sanitize(marked.parse(src) as string)
}

async function checkAdmin() {
  const t = localStorage.getItem('fpm_access_token')
  if (!t) return
  try {
    const r = await fetch('/api/v1/users/me', { headers: { Authorization: `Bearer ${t}` } })
    if (r.ok) canEditAnnouncement.value = ((await r.json()).discuss_perms || []).includes('announce')
  } catch { /* 非管理员/无效 token：不显示编辑按钮，不跳转登录 */ }
}

function openAnnounceEdit() {
  announceDraft.value = board.value?.announcement || ''
  announceEditVisible.value = true
}

async function saveAnnounce() {
  savingAnnounce.value = true
  try {
    const r = await discussApi.setAnnouncement(announceDraft.value)
    if (board.value) board.value.announcement = r.content
    announceEditVisible.value = false
  } catch {
    alert('保存失败（需要 PMS 管理员权限）')
  } finally {
    savingAnnounce.value = false
  }
}

const draft = ref('')
const draftAtts = ref<DiscussAttachment[]>([])
const imgCount = computed(() => draftAtts.value.filter((a) => a.type === 'image').length)
const vidCount = computed(() => draftAtts.value.filter((a) => a.type === 'video').length)
const sending = ref(false)
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const appendFor = ref<number | null>(null)
const appendDraft = ref('')

/* 登录/注册弹层 */
const authVisible = ref(false)
const authMode = ref<'login' | 'register'>('login')
const authEmail = ref('')
const authCode = ref('')
const authNickname = ref('')
const authPhone = ref('')
const authing = ref(false)
const authError = ref('')
const codeCooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  document.title = '用户留言区'
  const cached = localStorage.getItem('dsc_me')
  if (discussTokenStore.get() && cached) {
    try { me.value = JSON.parse(cached) } catch { /* 忽略损坏缓存 */ }
  }
  try {
    board.value = await discussApi.board()
  } catch {
    board.value = { enabled: false }
  }
  if (board.value?.enabled) checkAdmin()  // 公告编辑权限（不阻塞、不跳转）
  if (board.value?.enabled && me.value) await load()  // 仅登录用户加载（且只含本人留言）
})

async function load() {
  loading.value = true
  try {
    const r = await discussApi.threads(1, 10)
    threads.value = r.items
    total.value = r.total
    page.value = 1
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  loading.value = true
  try {
    const r = await discussApi.threads(page.value + 1, 10)
    threads.value = [...threads.value, ...r.items]
    page.value += 1
  } finally {
    loading.value = false
  }
}

/* ---- 登录 / 注册 ---- */

async function sendCode() {
  authError.value = ''
  try {
    await discussApi.requestCode(authEmail.value.trim())
    codeCooldown.value = 60
    if (cooldownTimer) clearInterval(cooldownTimer)
    cooldownTimer = setInterval(() => {
      codeCooldown.value -= 1
      if (codeCooldown.value <= 0 && cooldownTimer) clearInterval(cooldownTimer)
    }, 1000)
  } catch (e) {
    authError.value = (e as { detail?: string }).detail || '发送失败'
  }
}

async function doAuth() {
  authError.value = ''
  authing.value = true
  try {
    const r = authMode.value === 'login'
      ? await discussApi.login({ email: authEmail.value.trim(), code: authCode.value.trim() })
      : await discussApi.register({
          email: authEmail.value.trim(), code: authCode.value.trim(),
          nickname: authNickname.value.trim(), phone: authPhone.value.trim(),
        })
    discussTokenStore.set(r.token)
    me.value = { nickname: r.nickname, email: r.email }
    localStorage.setItem('dsc_me', JSON.stringify(me.value))
    authVisible.value = false
    authCode.value = ''
    await load()  // 登录后加载本人留言
  } catch (e) {
    authError.value = (e as { detail?: string }).detail || '操作失败'
  } finally {
    authing.value = false
  }
}

function logout() {
  discussTokenStore.clear()
  localStorage.removeItem('dsc_me')
  me.value = null
  threads.value = []   // 退出后不再展示任何留言
  total.value = 0
}

/* ---- 发帖 / 附件 ---- */

let pickAccept = ''
function pickFile(accept: string) {
  pickAccept = accept
  if (fileInput.value) {
    fileInput.value.accept = accept
    fileInput.value.value = ''
    fileInput.value.click()
  }
}

async function onFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const isVideo = pickAccept.includes('video')
  // 数量限额（防刷）：按类型拦在上传前，避免白传
  if (isVideo && vidCount.value >= MAX_VIDEOS) { alert(`最多上传 ${MAX_VIDEOS} 个视频`); return }
  if (!isVideo && imgCount.value >= MAX_IMAGES) { alert(`最多上传 ${MAX_IMAGES} 张图片`); return }
  const maxMB = isVideo ? 100 : 10
  if (file.size > maxMB * 1024 * 1024) {
    alert(`${isVideo ? '视频' : '图片'}不能超过 ${maxMB}MB`)
    return
  }
  uploading.value = true
  try {
    const att = await discussApi.upload(file)
    draftAtts.value.push(att)
  } catch (err) {
    alert((err as { detail?: string }).detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function submitRoot() {
  sending.value = true
  try {
    await discussApi.postMessage({ content: draft.value.trim(), attachments: draftAtts.value })
    draft.value = ''
    draftAtts.value = []
    await load()
  } catch (e) {
    alert((e as { detail?: string }).detail || '发布失败')
  } finally {
    sending.value = false
  }
}

async function submitAppend(threadId: number) {
  sending.value = true
  try {
    await discussApi.postMessage({ content: appendDraft.value.trim(), thread_id: threadId })
    appendFor.value = null
    appendDraft.value = ''
    await load()
  } catch (e) {
    alert((e as { detail?: string }).detail || '提交失败')
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
/* 移动端优先：单列窄版心，触控友好的按钮尺寸；桌面端只是加宽居中 */
.forum { max-width: 720px; margin: 0 auto; padding: 16px 14px 60px;
  font-family: var(--font-body, system-ui, sans-serif); color: var(--c-ink, #1a1a1a); }

.fm-head { margin-bottom: 14px; }
.fm-title-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.fm-title { font-size: 22px; font-weight: 800; margin: 0; }
.fm-user { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.fm-nick { font-weight: 600; font-size: 14px; color: var(--c-accent, #3a5bd9); }
.fm-welcome { margin: 6px 0 0; color: var(--c-ink-2, #55555f); font-size: 14px; }
.fm-closed { padding: 60px 0; text-align: center; color: var(--c-ink-3, #8a8a94); font-size: 15px; }

/* 发帖区 */
.fm-composer { background: var(--c-surface, #fff); border: 1px solid var(--c-border, #e7e5e0);
  border-radius: 12px; padding: 12px; margin-bottom: 18px; }
.fm-input { width: 100%; border: none; outline: none; resize: vertical; font-size: 15px;
  line-height: 1.6; font-family: inherit; background: transparent; }
.fm-composer-bar { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
.fm-tools { display: flex; align-items: center; gap: 10px; }
.fm-tool-btn { background: none; border: 1px solid var(--c-border, #e7e5e0); border-radius: 8px;
  padding: 6px 12px; font-size: 13px; cursor: pointer; color: var(--c-ink-2, #55555f); }
.fm-tool-btn:disabled { opacity: .4; cursor: not-allowed; }
.fm-uploading { font-size: 12px; color: var(--c-ink-3); }
.fm-send { background: var(--c-accent, #3a5bd9); color: #fff; border: none; border-radius: 8px;
  padding: 8px 22px; font-size: 14px; font-weight: 600; cursor: pointer; }
.fm-send:disabled { opacity: .4; cursor: not-allowed; }

/* 附件预览 */
.fm-att-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.fm-att-item { position: relative; }
.fm-att-thumb { width: 72px; height: 72px; object-fit: cover; border-radius: 8px; display: block; cursor: zoom-in; }
.fm-att-video { display: inline-block; padding: 8px 12px; background: var(--c-surface-2, #fbfaf8);
  border-radius: 8px; font-size: 12px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fm-att-del { position: absolute; top: -6px; right: -6px; width: 20px; height: 20px; border-radius: 50%;
  border: none; background: rgba(0,0,0,.6); color: #fff; font-size: 11px; cursor: pointer; line-height: 1; }

/* 留言楼 */
.fm-thread { background: var(--c-surface, #fff); border: 1px solid var(--c-border, #e7e5e0);
  border-radius: 12px; padding: 14px; margin-bottom: 12px; }
.fm-msg-head { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; margin-bottom: 4px; }
.fm-author { font-weight: 700; font-size: 14px; }
.fm-star { color: #f59e0b; font-size: 13px; letter-spacing: 1px; }
.fm-badge { background: var(--c-accent, #3a5bd9); color: #fff; font-size: 11px; padding: 1px 8px;
  border-radius: 999px; font-weight: 600; }
.fm-time { color: var(--c-ink-3, #8a8a94); font-size: 12px; margin-left: auto; }
.fm-content { margin: 0; font-size: 15px; line-height: 1.7; white-space: pre-wrap; word-break: break-word; }
.fm-reply { margin-top: 10px; padding: 10px 12px; background: var(--c-surface-2, #fbfaf8); border-radius: 10px; }
.fm-reply.official { background: var(--c-accent-soft, #e9edfb); }
.fm-append { margin-top: 10px; }
.fm-link-btn { background: none; border: none; color: var(--c-accent, #3a5bd9); font-size: 13px;
  cursor: pointer; padding: 4px 0; }
.fm-empty { text-align: center; color: var(--c-ink-3); padding: 40px 0; font-size: 14px; }
.fm-mine-tip { margin: 0 0 10px; font-size: 12px; color: var(--c-ink-3); }

/* 公告区 */
.fm-announce { background: var(--c-surface, #fff); border: 1px solid var(--c-border, #e7e5e0);
  border-left: 3px solid var(--c-accent, #3a5bd9); border-radius: 12px; padding: 12px 14px; margin-bottom: 16px; }
.fm-announce-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.fm-announce-title { font-weight: 700; font-size: 14px; color: var(--c-accent, #3a5bd9); }
.fm-announce-empty { color: var(--c-ink-3, #8a8a94); font-size: 13px; }

/* Markdown 渲染通用样式（公告 + 预览） */
.fm-md { font-size: 14px; line-height: 1.7; color: var(--c-ink, #1a1a1a); word-break: break-word; }
.fm-md :deep(h1) { font-size: 20px; margin: 8px 0; }
.fm-md :deep(h2) { font-size: 17px; margin: 8px 0; }
.fm-md :deep(h3) { font-size: 15px; margin: 6px 0; }
.fm-md :deep(p) { margin: 6px 0; }
.fm-md :deep(ul), .fm-md :deep(ol) { margin: 6px 0; padding-left: 22px; }
.fm-md :deep(a) { color: var(--c-accent, #3a5bd9); text-decoration: underline; }
.fm-md :deep(code) { background: var(--c-surface-2, #f4f3f0); padding: 1px 5px; border-radius: 4px; font-size: 13px; }
.fm-md :deep(pre) { background: var(--c-surface-2, #f4f3f0); padding: 10px; border-radius: 8px; overflow-x: auto; }
.fm-md :deep(pre code) { background: none; padding: 0; }
.fm-md :deep(blockquote) { margin: 6px 0; padding: 2px 12px; border-left: 3px solid var(--c-border, #e7e5e0); color: var(--c-ink-2, #55555f); }
.fm-md :deep(img) { max-width: 100%; border-radius: 8px; }
.fm-md :deep(hr) { border: none; border-top: 1px solid var(--c-border, #e7e5e0); margin: 10px 0; }
.fm-md :deep(table) { border-collapse: collapse; }
.fm-md :deep(th), .fm-md :deep(td) { border: 1px solid var(--c-border, #e7e5e0); padding: 4px 8px; }

/* 公告编辑弹层 */
.fm-announce-sheet { max-width: 620px; }
.fm-sheet-title { font-size: 16px; font-weight: 600; }
.fm-announce-input { width: 100%; box-sizing: border-box; min-height: 160px; resize: vertical;
  border: 1px solid var(--c-border, #e7e5e0); border-radius: 10px; padding: 10px 12px; font-size: 14px;
  line-height: 1.6; font-family: ui-monospace, Menlo, Consolas, monospace; outline: none; }
.fm-announce-input:focus { border-color: var(--c-accent, #3a5bd9); }
.fm-announce-preview-label { font-size: 12px; color: var(--c-ink-3, #8a8a94); margin: 10px 0 4px; }
.fm-announce-preview { border: 1px dashed var(--c-border, #e7e5e0); border-radius: 10px; padding: 10px 12px;
  max-height: 220px; overflow-y: auto; background: var(--c-surface-2, #fbfaf8); }
.fm-announce-actions { display: flex; justify-content: flex-end; align-items: center; gap: 12px; margin-top: 14px; }
.fm-more { display: block; width: 100%; padding: 12px; margin-top: 4px; background: none;
  border: 1px dashed var(--c-border); border-radius: 10px; color: var(--c-ink-2); cursor: pointer; font-size: 14px; }

/* 媒体展示：图片自适应宽度，视频响应式 */
.fm-media { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.fm-media-img { max-width: 100%; width: auto; max-height: 260px; border-radius: 10px;
  cursor: zoom-in; display: block; }
.fm-media-video { width: 100%; max-height: 320px; border-radius: 10px; background: #000; }
.fm-zoom { position: fixed; inset: 0; background: rgba(0,0,0,.85); z-index: 99;
  display: flex; align-items: center; justify-content: center; cursor: zoom-out; }
.fm-zoom-img { max-width: 96vw; max-height: 92vh; object-fit: contain; }

/* 登录 / 注册底部抽屉（移动端习惯；桌面端自动居中变窄卡） */
.fm-mask { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 50;
  display: flex; align-items: flex-end; justify-content: center; }
.fm-sheet { background: var(--c-surface, #fff); width: 100%; max-width: 480px;
  border-radius: 16px 16px 0 0; padding: 16px 18px 28px; }
@media (min-width: 640px) {
  .fm-mask { align-items: center; }
  .fm-sheet { border-radius: 16px; padding-bottom: 20px; }
}
.fm-sheet-head { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; }
.fm-tab { background: none; border: none; font-size: 17px; font-weight: 600; color: var(--c-ink-3);
  cursor: pointer; padding: 4px 2px; border-bottom: 2px solid transparent; }
.fm-tab.on { color: var(--c-ink); border-bottom-color: var(--c-accent, #3a5bd9); }
.fm-sheet-close { margin-left: auto; background: none; border: none; font-size: 16px;
  color: var(--c-ink-3); cursor: pointer; }
.fm-form { display: flex; flex-direction: column; gap: 10px; }
.fm-field { padding: 12px 14px; border: 1px solid var(--c-border, #e7e5e0); border-radius: 10px;
  font-size: 15px; outline: none; width: 100%; box-sizing: border-box; }
.fm-field:focus { border-color: var(--c-accent, #3a5bd9); }
.fm-code-row { display: flex; gap: 8px; }
.fm-code-row .fm-field { flex: 1; }
.fm-code-btn { flex-shrink: 0; padding: 0 14px; border: 1px solid var(--c-accent, #3a5bd9);
  background: none; color: var(--c-accent, #3a5bd9); border-radius: 10px; font-size: 13px; cursor: pointer; }
.fm-code-btn:disabled { opacity: .4; cursor: not-allowed; }
.fm-auth-submit { padding: 12px; font-size: 15px; }
.fm-error { color: #d94b3a; font-size: 13px; margin: 0; }
</style>
