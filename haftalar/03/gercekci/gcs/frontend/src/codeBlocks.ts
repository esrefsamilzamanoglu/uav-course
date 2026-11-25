import type { CodeFunction, CodeSource, MissionId, TraceEvent, TraceFrame, TraceLane } from './types'

export type BlockTone = 'amber' | 'blue' | 'violet' | 'orange' | 'teal' | 'rose' | 'slate'
export const BLOCK_COLORS: Record<BlockTone, string> = {
  amber: '#946200', blue: '#2563eb', violet: '#7c3aed', orange: '#c2410c',
  teal: '#0f766e', rose: '#be185d', slate: '#64748b',
}

export interface TeachingBlock {
  id: string
  label: string
  description: string
  tone: BlockTone
  color: string
  startLine: number
  endLine: number
  functionName: string
  file: string
  kind: 'mission' | 'function'
  /** Reachable plans only; this is not a completed-step indicator. */
  missions?: MissionId[]
}

interface Definition { label: string; tone: BlockTone; description: string }
interface Marker extends Definition { id: string; pattern: RegExp; missions?: MissionId[]; includePreviousElse?: boolean }

const DEFINITIONS: Record<string, Definition> = {
  'mission_steps': { label: 'Görev Planı', tone: 'amber', description: 'Seçilen görevin adımlarını hazırlar.' },
  'Controller.__init__': { label: 'Bağlantı Hazırlığı', tone: 'amber', description: 'Uçuş bağlantısını, görev durumunu ve izleyiciyi hazırlar.' },
  'Controller.start': { label: 'Alıcı Başlatma', tone: 'blue', description: 'MAVLink alıcı iş parçacığını başlatır.' },
  'Controller.close': { label: 'Güvenli Kapatma', tone: 'rose', description: 'Görev ve telemetri oturumunu kapatır.' },
  'Controller.send': { label: 'Komut Gönderme', tone: 'blue', description: 'MAVLink mesajlarını sırayla gönderir.' },
  'Controller.loop': { label: 'Telemetri Alımı', tone: 'blue', description: 'ArduPilot mesajlarını ve fizik geri bildirimini alır.' },
  'Controller.read_mechanics': { label: 'Fizik Ölçümü', tone: 'slate', description: 'Native fizik mesajını ve güncelliğini okur.' },
  'Controller.vehicle': { label: 'Telemetri Okuma', tone: 'slate', description: 'Ölçülen konum, hız ve araç durumunu oluşturur.' },
  'Controller.command': { label: 'Komut Onayı', tone: 'blue', description: 'Komutu gönderir; ArduPilot yanıtını bekler.' },
  'Controller.wait': { label: 'Koşul Bekleme', tone: 'slate', description: 'Ölçülen koşulu, bağlantıyı ve süre sınırını denetler.' },
  'Controller.mode': { label: 'Mod Değişimi', tone: 'blue', description: 'Uçuş modunu değiştirir ve doğrular.' },
  'Controller.servo': { label: 'Servo Kontrolü', tone: 'orange', description: 'Tutucunun açma veya kapama komutunu gönderir.' },
  'Controller.takeoff': { label: 'Kalkış Kontrolü', tone: 'amber', description: 'GUIDED, ARM ve kalkışı telemetriyle doğrular.' },
  'Controller.goto': { label: 'Konuma Git', tone: 'blue', description: 'Konum hedefini gönderir; uzaklık, yükseklik ve hız koşulunu bekler.' },
  'Controller.phase': { label: 'Aşama Kaydı', tone: 'slate', description: 'Gerçek görevin aşama bilgisini günceller.' },
  'Controller.grips': { label: 'Tutucu Durumu', tone: 'teal', description: 'Tutucuların fiziksel bağlantı durumunu okur.' },
  'Controller.gripper_pair': { label: 'Eşzamanlı Ölçüm', tone: 'teal', description: 'Gövdeyi ve tutucuyu aynı fizik mesajından okur.' },
  'Controller.gripper_offset': { label: 'Tutucu Ofseti', tone: 'teal', description: 'Aynı andaki ölçümlerden tutucu ofsetini hesaplar.' },
  'Controller.pickup_ready': { label: 'Yaklaşma Kontrolü', tone: 'teal', description: 'Ölçüm güncelliğini, yüksekliği ve askı durulmasını denetler.' },
  'Controller.visual_pickup_lock': { label: 'Görsel Kilit', tone: 'violet', description: 'Üç farklı, güncel RGB karesinden yük konumunu sabitler.' },
  'Controller.pickup': { label: 'Yük Kavrama', tone: 'teal', description: 'RGB ile yaklaşır, hizalar ve fiziksel kavramayı doğrular.' },
  'Controller.release': { label: 'Yük Bırakma', tone: 'orange', description: 'Boş alana hizalar, salınımı bekler ve yükü bırakır.' },
  'Controller.mission_start': { label: 'Görev Başlatma', tone: 'amber', description: 'Seçilen görev için yeni çalışma başlatır.' },
  'Controller._run_traced_mission': { label: 'Kod İzleme', tone: 'slate', description: 'Görev iş parçacığının gerçek Python izini toplar.' },
  'Controller.run_mission': { label: 'Görev Akışı', tone: 'slate', description: 'Seçilen G1, G2 veya G3 görevinin gerçek kaynak akışını yürütür.' },
  'rotation': { label: 'Kamera Yönelimi', tone: 'violet', description: 'Kamera yönelimini dönüş matrisine çevirir.' },
  'project': { label: 'Piksel Konumu', tone: 'violet', description: 'Piksel ışınını dünyadaki zeminle kesiştirir.' },
  'masks': { label: 'Renk Maskesi', tone: 'violet', description: 'Kırmızı ve mavi piksel maskelerini çıkarır.' },
  'detect': { label: 'Hedef Tespiti', tone: 'violet', description: 'Renk, boyut ve şekil ölçümlerinden gerçek tespit üretir.' },
  'select_drop_point': { label: 'Boş Alan', tone: 'orange', description: 'Görülen çokgende kenarlardan ve diğer yükten uzak yer seçer.' },
  'read_frame': { label: 'Kare Doğrulama', tone: 'violet', description: 'Görüntü ve kamera pozunun eşleşmesini, boyutunu ve yaşını denetler.' },
  'Camera.__init__': { label: 'Kamera Hazırlığı', tone: 'amber', description: 'Kamera alıcısını ve tespit belleğini hazırlar.' },
  'Camera.start': { label: 'Kamera Başlatma', tone: 'violet', description: 'Gerçek Gazebo karelerini okumayı başlatır.' },
  'Camera.close': { label: 'Kamera Kapatma', tone: 'slate', description: 'Kamera iş parçacığını durdurur.' },
  'Camera.loop': { label: 'Kare Döngüsü', tone: 'violet', description: 'Yeni kamera karelerini düzenli aralıklarla okur.' },
  'Camera.update': { label: 'Kare İşleme', tone: 'violet', description: 'Gerçek kareyi doğrular, tespitleri işler ve görüntüyü günceller.' },
  'Camera.state': { label: 'Kamera Durumu', tone: 'slate', description: 'Görüntünün mevcut ve güncel olup olmadığını sunar.' },
  'Camera.target_polygon': { label: 'Hedef Sınırı', tone: 'orange', description: 'Güncel görüntüden çıkarılan hedef sınırını okur.' },
  'Camera.confirmed': { label: 'Hedef Kaydı', tone: 'violet', description: 'Birden çok kareyle doğrulanan tespitleri sunar.' },
  'Service.__init__': { label: 'Servis Hazırlığı', tone: 'amber', description: 'Yerel GCS servisini hazırlar.' },
  'Service.start': { label: 'Simülasyon Başlatma', tone: 'amber', description: 'Gazebo, kamera ve uçuş denetleyicisini başlatır.' },
  'Service.close': { label: 'Simülasyon Kapatma', tone: 'rose', description: 'Yerel simülasyon oturumunu kapatır.' },
  'Service.event': { label: 'Olay Kaydı', tone: 'slate', description: 'Operatöre gösterilen olay kaydını ekler.' },
  'Service.snapshot': { label: 'Durum Toplama', tone: 'slate', description: 'GCS için ölçülen verileri bir araya getirir.' },
  'Service.execute': { label: 'Komut Dağıtımı', tone: 'blue', description: 'Operatörün seçtiği komutu ilgili işleme yönlendirir.' },
  'Service.safe_task': { label: 'Komut Koruması', tone: 'rose', description: 'Komut hatalarını operatöre bildirir.' },
  'Service.map_jpeg': { label: 'Harita Görüntüsü', tone: 'violet', description: 'Gerçek saha görüntüsünü GCS için hazırlar.' },
  'Handler.reply': { label: 'Yanıt Gönderme', tone: 'blue', description: 'Yerel HTTP yanıtını gönderir.' },
  'Handler.do_GET': { label: 'Veri Okuma', tone: 'blue', description: 'Durum, kaynak ve görüntü isteklerini karşılar.' },
  'Handler.do_POST': { label: 'Komut Alma', tone: 'blue', description: 'Yerel operatör komutunu alır.' },
  'Handler.do_OPTIONS': { label: 'Kaynak Kontrolü', tone: 'slate', description: 'Yerel erişim seçeneklerini yanıtlar.' },
  'Handler.log_message': { label: 'Erişim Kaydı', tone: 'slate', description: 'HTTP günlük davranışını belirler.' },
  'NativeRuntime.__init__': { label: 'Çalışma Hazırlığı', tone: 'amber', description: 'Native süreç oturumu için durumu hazırlar.' },
  'NativeRuntime.start': { label: 'Simülasyon Başlatma', tone: 'amber', description: 'Dünya ve native süreçleri başlatır.' },
  'NativeRuntime.close': { label: 'Simülasyon Kapatma', tone: 'rose', description: 'Oturuma ait native süreçleri kapatır.' },
  'NativeRuntime.running': { label: 'Çalışma Durumu', tone: 'slate', description: 'Native oturumun çalıştığını denetler.' },
  'main': { label: 'Servis Başlatma', tone: 'amber', description: 'Yerel uygulama başlatıcısını çalıştırır.' },
}

const FALLBACK: Definition = { label: 'Python İşlemi', tone: 'slate', description: 'Bu bölümün gerçek Python kaynak satırları gösterilir.' }
const ALL_MISSIONS: MissionId[] = ['G1', 'G2', 'G3']

const MISSION_MARKERS: Marker[] = [
  { id: 'entry', pattern: /^\s*self\.goto\(\[-40,-105,/, label: 'Alan Geçişi', tone: 'blue', description: 'Direk 2 dışındaki giriş koridoruna gider.', missions: ALL_MISSIONS },
  { id: 'eights', pattern: /^\s*if mission==['"]G1['"]:\s*$/, label: 'Sekiz Uçuşu', tone: 'blue', description: 'İki ardışık sekiz turunun rota noktalarını izler.', missions: ['G1'] },
  { id: 'exit', pattern: /^\s*self\.phase\(4,['"]İki sekiz/, label: 'Dış Koridor', tone: 'blue', description: 'Tamamlanan sekizlerden sonra dış koridora çıkar.', missions: ['G1'] },
  { id: 'search', pattern: /^\s*self\.phase\(2\);self\.camera\.perception_enabled=True/, label: 'Hedef Arama', tone: 'violet', description: 'Alanı tarar; iki hedefi gerçek kamera görüntüsünde doğrular.', missions: ['G2', 'G3'], includePreviousElse: true },
  { id: 'deliver', pattern: /^\s*targets=list\(self\.camera\.estimates\.items\(\)\)/, label: 'Yük Bırakma', tone: 'orange', description: 'Görülen hedeflere yaklaşır ve iki ilk teslimatı yapar.', missions: ['G2', 'G3'] },
  { id: 'pickup', pattern: /^\s*if mission==['"]G3['"]:\s*$/, label: 'Yük Kavrama', tone: 'teal', description: 'İlk bırakılan yükü RGB ile yeniden bulup kavrar.', missions: ['G3'] },
  { id: 'transfer', pattern: /^\s*self\.phase\(4,['"]G3/, label: 'Hedefe Taşıma', tone: 'teal', description: 'Kavranan ilk yükü diğer hedefteki boş alana taşır.', missions: ['G3'] },
  { id: 'return', pattern: /^\s*self\.phase\(5\)/, label: 'HOME Dönüşü', tone: 'blue', description: 'Göreve uygun dönüş koridorundan HOME üzerine gelir.', missions: ALL_MISSIONS },
  { id: 'landing', pattern: /^\s*self\.mode\(9\);self\.wait/, label: 'İniş Kontrolü', tone: 'rose', description: 'LAND moduna geçer ve normal DISARM geri bildirimini bekler.', missions: ALL_MISSIONS },
  { id: 'failure', pattern: /^\s{8}except Exception as e:/, label: 'Güvenli Bekleme', tone: 'rose', description: 'Gerçek hatayı kaydeder; gerekli durumda BRAKE seçer.', missions: ALL_MISSIONS },
  { id: 'record', pattern: /^\s{8}finally:/, label: 'Görev Kaydı', tone: 'slate', description: 'Kamera alımını temizler ve gerçek görev sonucunu kaydeder.', missions: ALL_MISSIONS },
]

const OPERATION_MARKERS: Record<string, Marker[]> = {
  'Controller.pickup': [
    { id: 'approach', pattern: /^\s*for height in \(2\.0,1\.2\)/, label: 'Alçak Yaklaşma', tone: 'blue', description: 'RGB yük konumuna eşzamanlı tutucu ölçümüyle alçalır.' },
    { id: 'lock', pattern: /^\s*locked,seen=self\.visual_pickup_lock/, label: 'Görsel Kilit', tone: 'violet', description: 'Üç güncel RGB gözleminden kısa süreli yük kilidi alır.' },
    { id: 'align', pattern: /^\s*aligned=False/, label: 'Hassas Hizalama', tone: 'teal', description: 'Son alçalmada tutucuyu görsel kilidin üzerinde hizalar.' },
    { id: 'grasp', pattern: /^\s*remaining\(\);self\.servo\(channel,1900\)/, label: 'Yükü Kavra', tone: 'teal', description: 'Servo kapatır ve fiziksel bağlantı geri bildirimini bekler.' },
    { id: 'cleanup', pattern: /^\s{8}finally:/, label: 'Algıyı Kapat', tone: 'slate', description: 'Kavrama denemesinin özel yük algısını kapatır.' },
  ],
  'Controller.release': [
    { id: 'space', pattern: /^\s*drop_point=list\(target\)/, label: 'Bırakma Noktası', tone: 'orange', description: 'Bırakma noktasını belirler; gerektiğinde RGB çokgeninde boş yer seçer.' },
    { id: 'align', pattern: /^\s*for _ in range\(3\):/, label: 'Bırakma Hizası', tone: 'blue', description: 'Eşzamanlı gövde ve tutucu ölçümleriyle bırakma noktasına hizalar.' },
    { id: 'settle', pattern: /^\s*def settled\(\):/, label: 'Salınım Kontrolü', tone: 'orange', description: 'Yükün salınımının ve yatay hızının azalmasını bekler.' },
    { id: 'release', pattern: /^\s*self\.servo\(ch,1100\)/, label: 'Yükü Bırak', tone: 'orange', description: 'Servo açar ve gerçek fizik ekleminin ayrılmasını bekler.' },
    { id: 'record', pattern: /^\s*record=dict\(color=color,target=/, label: 'Teslimat Kaydı', tone: 'slate', description: 'Asıl hedefi, seçilen boş noktayı ve teslimatı kaydeder.' },
  ],
  'Camera.update': [
    { id: 'detect', pattern: /^\s*detections=detect\(/, label: 'Hedef Tespiti', tone: 'violet', description: 'Gerçek RGB karesinde hedef ve istenen yükü arar.' },
    { id: 'track', pattern: /^\s*with self\.lock:/, label: 'Tespit Kaydı', tone: 'teal', description: 'Tespitleri, hedef sınırlarını ve çok kareli konum ölçümlerini günceller.' },
    { id: 'image', pattern: /^\s*ok,jpeg=cv2\.imencode/, label: 'Canlı Görüntü', tone: 'blue', description: 'GCS görüntüsünü ve kare güncelliğini hazırlar.' },
  ],
}

function definitionFor(name: string): Definition {
  if (DEFINITIONS[name]) return DEFINITIONS[name]
  // Nested Python helpers/lambdas belong to the named outer operation.
  let parent = name
  while (parent.includes('.')) {
    parent = parent.slice(0, parent.lastIndexOf('.'))
    if (DEFINITIONS[parent]) return DEFINITIONS[parent]
  }
  return FALLBACK
}

export function getBlockLabel(frame: TraceFrame | null | undefined): string {
  return frame ? definitionFor(frame.function).label : FALLBACK.label
}

function sections(source: CodeSource, fn: CodeFunction): TeachingBlock[] {
  const mission = fn.name === 'Controller.run_mission'
  const base = definitionFor(fn.name)
  const knownPreparation = mission && source.lines.slice(fn.line - 1, fn.end_line).some(line => /^\s*self\.phase\(0\)/.test(line))
  const initial = knownPreparation
    ? { label: 'Uçuş Hazırlığı', tone: 'amber' as const, description: 'GPS, EKF, ön yükleme ve kalkış koşullarını hazırlar.' }
    : fn.name === 'Controller.pickup'
    ? { label: 'Yükü Ara', tone: 'violet' as const, description: 'İlk teslimatın yakınında güncel RGB yük görüntüsünü arar.' }
    : fn.name === 'Controller.release'
      ? { label: 'Hedefe Yaklaş', tone: 'blue' as const, description: 'Görülen hedef üzerine dört metreye yaklaşır.' }
      : fn.name === 'Camera.update'
        ? { label: 'Kare Doğrulama', tone: 'violet' as const, description: 'Yeni görüntü ve kamera pozu eşleşmesini doğrular.' }
        : base
  const anchors: { line: number; id: string; definition: Definition; missions?: MissionId[] }[] = [
    { line: fn.line, id: 'start', definition: initial, missions: mission ? ALL_MISSIONS : undefined },
  ]
  const markers = mission ? MISSION_MARKERS : OPERATION_MARKERS[fn.name] ?? []
  for (const marker of markers) {
    for (let line = fn.line; line <= fn.end_line; line += 1) {
      if (!marker.pattern.test(source.lines[line - 1] ?? '')) continue
      const start = marker.includePreviousElse && /^\s*else:\s*$/.test(source.lines[line - 2] ?? '') ? line - 1 : line
      anchors.push({ line: start, id: marker.id, definition: marker, missions: marker.missions })
      break
    }
  }
  anchors.sort((a, b) => a.line - b.line)
  return anchors.map((anchor, index) => ({
    id: `${source.file}:${fn.name}:${anchor.id}`,
    label: anchor.definition.label,
    description: anchor.definition.description,
    tone: anchor.definition.tone,
    color: BLOCK_COLORS[anchor.definition.tone],
    startLine: anchor.line,
    endLine: anchors[index + 1] ? anchors[index + 1].line - 1 : fn.end_line,
    functionName: fn.name,
    file: source.file,
    kind: mission ? 'mission' : 'function',
    missions: anchor.missions,
  }))
}

/** Build from the exact cached source shown with its SHA, never from disk lines. */
export function buildCodeBlocks(source: CodeSource | null | undefined): TeachingBlock[] {
  if (!source?.lines.length) return []
  const functions = source.functions.filter(fn => Number.isInteger(fn.line) && Number.isInteger(fn.end_line)
    && fn.line >= 1 && fn.end_line >= fn.line && fn.end_line <= source.lines.length)
  // Inner ready/consistent/settled helpers stay inside their teaching section.
  const outer = functions.filter(fn => !functions.some(parent => parent !== fn
    && parent.line < fn.line && parent.end_line >= fn.end_line)).sort((a, b) => a.line - b.line)
  return outer.flatMap(fn => sections(source, fn))
}

export function findCodeBlock(blocks: readonly TeachingBlock[], line: number | undefined): TeachingBlock | undefined {
  if (line == null || !Number.isInteger(line)) return undefined
  return blocks.find(block => line >= block.startLine && line <= block.endLine)
}

export interface TeachingFocus extends TraceFrame { isCaller: boolean }

/** A stable real caller, not an animation inferred from mission.phase. */
export function getTeachingFocus(event: TraceEvent | null | undefined, lane: TraceLane): TeachingFocus | null {
  if (!event) return null
  const stack = event.stack ?? []
  const parentName = lane === 'mission' ? 'Controller.run_mission' : 'Camera.update'
  const parent = stack.find(frame => frame.function === parentName)
  const frame = parent ?? event
  return { file: frame.file, function: frame.function, line: frame.line ?? frame.lineno ?? 0,
    isCaller: Boolean(parent && (parent.file !== event.file || parent.line !== event.line || parent.function !== event.function)) }
}
