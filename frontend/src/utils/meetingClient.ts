/* 本端浏览器唯一 id（localStorage 持久化）。
 * 用于会议计时主控认领/续权，以及"结束会议"时校验是否主控端。
 * 同一浏览器跨页面（汇报页 / 看板开关）共用同一 id。 */
const CLIENT_ID_KEY = 'fpm_meeting_client_id'

export function getMeetingClientId(): string {
  let id = localStorage.getItem(CLIENT_ID_KEY)
  if (!id) {
    id = `c-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
    localStorage.setItem(CLIENT_ID_KEY, id)
  }
  return id
}
