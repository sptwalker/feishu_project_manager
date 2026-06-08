<template>
  <div class="login">
    <!-- 左侧品牌氛围区 -->
    <div class="brand-panel">
      <div class="brand-content">
        <div class="brand-row">
          <span class="brand-mark">{{ branding.data.brand_mark }}</span>
          <span class="brand-name" v-html="branding.data.brand_login"></span>
        </div>
        <h1 class="headline" v-html="branding.data.login_headline"></h1>
        <p class="sub">{{ branding.data.login_sub }}</p>
      </div>
      <div class="grid-deco" aria-hidden="true"></div>
    </div>

    <!-- 右侧登录区 -->
    <div class="form-panel">
      <div class="form-card">
        <h2 class="form-title">登录</h2>
        <p class="form-desc">使用飞书账号一键登录，无需单独注册。</p>

        <button class="feishu-btn" :disabled="loading" @click="loginWithFeishu">
          <span class="feishu-ico">✦</span>
          {{ loading ? '正在跳转…' : '飞书一键登录' }}
        </button>

        <p class="terms">登录即代表同意《服务条款》与《隐私政策》</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useBrandingStore } from '@/stores/branding'

const loading = ref(false)
const branding = useBrandingStore()

function loginWithFeishu() {
  loading.value = true
  // 跳转到后端飞书 OAuth 登录入口
  window.location.href = '/api/v1/auth/feishu/login'
}
</script>

<style scoped>
.login {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  height: 100vh;
}
@media (max-width: 860px) {
  .login { grid-template-columns: 1fr; }
  .brand-panel { display: none; }
}

/* 品牌区 */
.brand-panel {
  position: relative;
  background: var(--c-sidebar);
  color: var(--c-on-dark);
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: var(--sp-7);
}
.brand-content { position: relative; z-index: 2; max-width: 460px; }
.brand-row { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-7); }
.brand-mark {
  width: 40px; height: 40px;
  display: grid; place-items: center;
  background: var(--c-accent); color: #fff;
  border-radius: var(--r-md);
  font-family: var(--font-display); font-weight: 700; font-size: 19px;
}
.brand-name { font-family: var(--font-display); font-weight: 700; font-size: 21px; }
/* v-html 注入的强调字（品牌名/标语里的 .accent）需 :deep 穿透 scoped */
.brand-content :deep(.accent) { color: var(--c-accent); }
.headline {
  font-family: var(--font-display);
  font-size: 46px;
  line-height: 1.1;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: #fff;
  margin-bottom: var(--sp-4);
}
.sub { color: var(--c-on-dark-dim); font-size: 16px; }

/* 网格装饰 */
.grid-deco {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(var(--c-sidebar-hover) 1px, transparent 1px),
    linear-gradient(90deg, var(--c-sidebar-hover) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(circle at 75% 30%, #000 0%, transparent 70%);
  opacity: 0.5;
}

/* 表单区 */
.form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--sp-6);
  background: var(--c-canvas);
}
.form-card {
  width: 100%;
  max-width: 380px;
}
.form-title { font-size: 30px; margin-bottom: var(--sp-2); }
.form-desc { color: var(--c-ink-3); margin-bottom: var(--sp-6); }

.feishu-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-3);
  padding: 14px 18px;
  background: var(--c-accent);
  color: #fff;
  border: none;
  border-radius: var(--r-md);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 15px;
  cursor: pointer;
  box-shadow: var(--shadow-md);
  transition: background 0.15s, transform 0.1s;
}
.feishu-btn:hover:not(:disabled) { background: var(--c-accent-hover); transform: translateY(-1px); }
.feishu-btn:disabled { opacity: 0.7; cursor: default; }
.feishu-ico { font-size: 16px; }

.terms { margin-top: var(--sp-5); font-size: 12px; color: var(--c-ink-3); text-align: center; }
</style>
