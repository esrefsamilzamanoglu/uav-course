/** UI fixtures only: all API requests are intercepted; no real flight commands. */
import { chromium, expect } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const output = path.resolve(here, '../.local/qa-student')
await fs.mkdir(output, { recursive: true })
const scene = JSON.parse(await fs.readFile(path.resolve(here, '../../../world/scene.json'), 'utf8'))
const bounds = scene.field_bounds
scene.field_bounds = { east_min: bounds.east[0], east_max: bounds.east[1], north_min: bounds.north[0], north_max: bounds.north[1] }
let state = {
  connected: true, simulation: { running: true, status: 'fixture' },
  vehicle: { armed: false, mode: 'GUIDED', ekf_ok: true, position_enu: [-24, 0, .9], last_heartbeat_age_s: .1 },
  mission: { id: 'G2', status: 'idle', phase: 'idle', steps: [] },
  camera: { available: true, frame_id: 1, width: 960, height: 720, age_s: .1 },
  follow_camera: { available: true, frame_id: 1, mode: 'chase', requested_mode: 'chase', age_s: .1 },
  scene, detections: [], confirmed_detections: [], grippers: {}, events: [], trail: [],
}
const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="720"><rect width="960" height="720" fill="#617851"/><text x="25" y="45" fill="white">UI TEST FIXTURE</text></svg>'
const browser = await chromium.launch({ executablePath: process.env.ROTA_CHROME, headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })
const commands = [], errors = [], checks = []
page.on('pageerror', error => errors.push(error.message))
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
await page.route('**/api/**', async route => {
  const request = route.request(), url = new URL(request.url())
  if (request.method() === 'POST') { commands.push(request.postDataJSON()); return route.fulfill({ json: { ok: true } }) }
  if (url.pathname === '/api/state') return route.fulfill({ json: state })
  if (url.pathname.endsWith('.jpg')) return route.fulfill({ contentType: 'image/svg+xml', body: svg })
  return route.fulfill({ json: {} })
})
try {
  await page.goto(process.env.ROTA_TEST_URL ?? 'http://127.0.0.1:5173', { waitUntil: 'domcontentloaded' })
  for (const id of ['G1', 'G2', 'G3']) {
    const choice = page.getByRole('button', { name: new RegExp(`^${id} `) }).first()
    await choice.click(); await expect(choice).toHaveAttribute('aria-pressed', 'true')
    await page.getByRole('button', { name: `${id} Görevini Başlat`, exact: true }).click()
    await expect.poll(() => commands.at(-1)?.mission).toBe(id)
    checks.push(`${id} seçimi ve doğru komut`)
  }
  await page.getByRole('button', { name: 'Sistem', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Mission Planner', exact: true })).toBeVisible()
  await expect(page.getByText('5762', { exact: true })).toBeVisible()
  await expect(page.getByText('127.0.0.1', { exact: true })).toBeVisible()
  await expect(page.getByText('Bağlantıya hazır', { exact: true })).toBeVisible()
  await expect(page.locator('.planner-connection')).toContainText('5760 · ayrı bağlantı')
  checks.push('Mission Planner bağlantı kartı ve ayrı portlar')
  await page.screenshot({ path: path.join(output, 'system-ready.png') })
  state = { ...state, connected: false, simulation: { running: false, status: 'stopped' } }
  await expect(page.getByText('Simülasyon bekleniyor', { exact: true })).toBeVisible({ timeout: 10000 })
  checks.push('Kapalı simülasyonda hazır durumu gösterilmez')
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('heading', { name: 'Mission Planner', exact: true })).toBeVisible()
  if (!await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)) throw new Error('Mobile horizontal overflow')
  await page.screenshot({ path: path.join(output, 'system-mobile.png'), fullPage: true })
  checks.push('390 px mobil görünüm')
  if (errors.length) throw new Error(JSON.stringify(errors))
  checks.push('Tarayıcı hatası yok')
  console.log(JSON.stringify({ passed: true, checks, fixture_only: true, commands }, null, 2))
} finally {
  await fs.writeFile(path.join(output, 'report.json'), JSON.stringify({ checks, errors, commands, fixture_only: true }, null, 2))
  await browser.close()
}
