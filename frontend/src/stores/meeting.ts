import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { settingsApi, meetingApi } from '@/api/resources'
import { getMeetingClientId } from '@/utils/meetingClient'
import type { MeetingState } from '@/types'

export const useMeetingStore = defineStore('meeting', () => {
  const state = ref<MeetingState | null>(null)
  const loaded = ref(false)

  const active = computed(() => state.value?.active ?? false)
  /** 当前（本周）周会次数 —— 周会模式下记录用此次数 */
  const currentCount = computed(() => state.value?.this_week_count ?? 0)

  async function load() {
    try {
      state.value = await settingsApi.getMeeting()
    } catch {
      state.value = null
    } finally {
      loaded.value = true
    }
    return state.value
  }

  async function setActive(next: boolean) {
    state.value = await settingsApi.setMeetingActive(next)
    return state.value
  }

  async function setCount(count: number) {
    state.value = await settingsApi.setMeetingCount(count)
    return state.value
  }

  /** 开启周会：确认计次/记录人/会议日期后开启，并刷新状态 */
  async function openMeeting(payload: { session: number; recorder?: string | null; meeting_date: string }) {
    const detail = await meetingApi.open(payload)
    await load()
    return detail
  }

  /** 关闭周会：归档当前周会并关闭模式，刷新状态。带本端 client_id 供后端校验是否主控。 */
  async function closeMeeting() {
    state.value = await meetingApi.close(getMeetingClientId())
    return state.value
  }

  return { state, loaded, active, currentCount, load, setActive, setCount, openMeeting, closeMeeting }
})
