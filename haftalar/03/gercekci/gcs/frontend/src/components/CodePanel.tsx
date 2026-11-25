import { memo, useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { Braces, ChevronRight, Code2, History, Layers3, LocateFixed, Pause, Play, Radio, TriangleAlert } from 'lucide-react'
import { useCodeSource, useCodeTrace } from '../codeApi'
import { buildCodeBlocks, findCodeBlock, getBlockLabel, getTeachingFocus } from '../codeBlocks'
import type { TeachingBlock } from '../codeBlocks'
import type { CodeTrace, GcsState, MissionId, TraceEvent, TraceLane } from '../types'
import { duration, number } from '../format'

const EVENT_LABELS = { line: 'Satır', call: 'Çağrı', return: 'Dönüş', exception: 'İstisna' }
const STATUS_LABELS: Record<string, string> = { running: 'Çalışıyor', paused: 'Bekletildi', completed: 'Tamamlandı', failed: 'Başarısız', idle: 'Çalışma bekleniyor', cancelled: 'Durduruldu' }

function blockStyle(block?: TeachingBlock): CSSProperties {
  return { '--block-color': block?.color ?? '#64748b' } as CSSProperties
}

const SourceLine = memo(function SourceLine({ text, line, current, caller, selected, exception, block, activeBlock }: { text: string; line: number; current: boolean; caller: boolean; selected: boolean; exception: boolean; block?: TeachingBlock; activeBlock: boolean }) {
  return <div className={['source-line', current && 'current', caller && 'caller', selected && 'inspected', exception && current && 'exception', activeBlock && 'in-active-block'].filter(Boolean).join(' ')} style={blockStyle(block)} data-line={line} data-current={current || undefined} data-caller={caller || undefined} data-teaching-block={block?.id}><span className="source-line-number">{current || caller ? <ChevronRight size={13} /> : null}{line}</span><code>{text || ' '}</code>{caller ? <span className="caller-line-label">Üst çağrı</span> : null}</div>
})

export function CodePanel({ state, selected }: { state: GcsState; selected: MissionId }) {
  const live = useCodeTrace()
  const [lane, setLane] = useState<TraceLane>('mission')
  const [file, setFile] = useState('control.py')
  const [blockView, setBlockView] = useState(true)
  const [autoFollow, setAutoFollow] = useState(true)
  const [followEpoch, setFollowEpoch] = useState(0)
  const [frozen, setFrozen] = useState<{ trace: CodeTrace; history: TraceEvent[] } | null>(null)
  const [inspected, setInspected] = useState<TraceEvent | null>(null)
  const [jumpLine, setJumpLine] = useState<number | null>(null)
  const [fontSize, setFontSize] = useState(14)
  const viewport = useRef<HTMLDivElement>(null)
  const blockNavigation = useRef<HTMLDivElement>(null)
  const trace = frozen?.trace ?? live.trace
  const history = frozen?.history ?? live.history
  const stale = Boolean(live.error) && !frozen
  const current = lane === 'mission' ? trace.current ?? trace.lanes?.mission : trace.lanes?.vision
  const displayed = inspected ?? current
  const focus = blockView && !inspected ? getTeachingFocus(current, lane) : displayed ? { file: displayed.file, line: displayed.line ?? displayed.lineno ?? 0, function: displayed.function, isCaller: false } : null
  const followedFile = autoFollow && !inspected && focus?.file ? focus.file : file
  const catalogFile = live.files.find(item => item.file === followedFile)
  const expectedSha = trace.source_sha256?.[followedFile] ?? catalogFile?.sha256
  const { source, error: sourceError, loading } = useCodeSource(followedFile, expectedSha)
  const executionSha = source ? trace.source_sha256?.[source.file] : undefined
  const sourceMatchesExecution = Boolean(source && executionSha && source.sha256 === executionSha)
  const actualLine = sourceMatchesExecution && current && current.file === source?.file ? current.line ?? current.lineno : undefined
  const focusLine = sourceMatchesExecution && focus?.file === source?.file ? focus?.line : undefined
  const inspectedLine = inspected
    ? sourceMatchesExecution && inspected.file === source?.file ? inspected.line ?? inspected.lineno : undefined
    : jumpLine
  const scrollLine = autoFollow ? focusLine ?? actualLine : inspectedLine
  const sourceOnly = Boolean(source && !source.trace_enabled)
  const functionLine = autoFollow ? focusLine ?? 0 : inspectedLine ?? 0
  const activeFunction = source?.functions.filter(fn => functionLine >= fn.line && functionLine <= fn.end_line).sort((a, b) => (a.end_line - a.line) - (b.end_line - b.line))[0]
  const executionFunction = displayed?.file === source?.file ? source?.functions.filter(fn => (displayed?.line ?? 0) >= fn.line && (displayed?.line ?? 0) <= fn.end_line).sort((a, b) => (a.end_line - a.line) - (b.end_line - b.line))[0] : undefined
  const blocks = useMemo(() => buildCodeBlocks(source), [source])
  const rows = useMemo(() => source?.lines.map((text, index) => ({ text, line: index + 1, block: findCodeBlock(blocks, index + 1) })) ?? [], [source, blocks])
  const liveBlock = sourceMatchesExecution ? findCodeBlock(blocks, focusLine ?? actualLine) : undefined
  const viewedBlock = !autoFollow || inspected ? findCodeBlock(blocks, inspectedLine ?? undefined) ?? liveBlock ?? blocks[0] : liveBlock
  const historyMission = inspected?.context?.mission
  const blockMission = historyMission === 'G1' || historyMission === 'G2' || historyMission === 'G3' ? historyMission : trace.mission_id ?? selected
  const missionBlocks = blocks.filter(block => block.kind === 'mission' && (!block.missions?.length || block.missions.includes(blockMission)))
  const navigationBlocks = blockView && missionBlocks.length ? missionBlocks : blocks.filter(block => block.kind === 'function')
  const wait = inspected || stale ? null : current?.wait
  const phaseLabel = inspected
    ? inspected.context?.phase_label ?? inspected.phase ?? inspected.context?.phase ?? 'Bu olayda aşama kaydı yok'
    : displayed?.context?.phase_label ?? (state.mission.id === trace.mission_id ? state.mission.phase_label : null) ?? displayed?.phase ?? '—'
  const recent = history.filter(event => event.lane === lane).slice(-60).reverse()
  const laneFresh = Boolean(current && typeof current.age_s === 'number' && current.age_s <= 2)
  const liveLane = !frozen && !stale && laneFresh && (lane === 'vision' || trace.active)
  const executionVisible = sourceMatchesExecution && !sourceOnly && !stale
  const blockActive = executionVisible && !inspected && (liveLane || Boolean(frozen))
  const callerLine = blockView && focus?.isCaller ? focusLine : undefined
  const bannerStatus = inspected ? 'Geçmiş blok' : !autoFollow ? 'İncelenen blok' : stale ? 'Son kayıt' : frozen ? 'Ekran sabit' : liveLane ? 'Çalışan blok' : 'Son blok'
  const bannerBlock = viewedBlock

  useEffect(() => {
    const container = viewport.current
    const row = scrollLine && container?.querySelector<HTMLElement>('[data-line="' + scrollLine + '"]')
    if (container && row) container.scrollTop = Math.max(0, row.offsetTop - container.clientHeight / 2 + row.clientHeight / 2)
  }, [scrollLine, source, fontSize, blockView, followEpoch])

  useEffect(() => {
    if (!autoFollow || !blockActive || !liveBlock) return
    const container = blockNavigation.current
    if (!container) return
    const centerActive = () => {
      const chip = container.querySelector<HTMLElement>('[data-block-id="' + liveBlock.id + '"]')
      if (chip) container.scrollLeft = Math.max(0, chip.offsetLeft - (container.clientWidth - chip.clientWidth) / 2)
    }
    centerActive()
    const observer = new ResizeObserver(centerActive)
    observer.observe(container)
    return () => observer.disconnect()
  }, [liveBlock?.id, autoFollow, blockActive, blockView, source, followEpoch])

  function follow(nextLane = lane) {
    const nextEvent = nextLane === 'mission' ? trace.current ?? trace.lanes?.mission : trace.lanes?.vision
    const nextFocus = blockView ? getTeachingFocus(nextEvent, nextLane) : nextEvent
    if (nextFocus?.file) setFile(nextFocus.file)
    setLane(nextLane)
    setAutoFollow(true)
    setInspected(null)
    setJumpLine(null)
    setFollowEpoch(epoch => epoch + 1)
  }
  function inspect(event: TraceEvent) {
    setInspected(event)
    setFile(event.file)
    setJumpLine(event.line ?? event.lineno ?? null)
    setAutoFollow(false)
  }
  function jumpToBlock(block: TeachingBlock) {
    setFile(block.file)
    setAutoFollow(false)
    setInspected(null)
    setJumpLine(block.startLine)
  }
  function changeView(next: boolean) {
    setBlockView(next)
    setAutoFollow(true)
    setInspected(null)
    setJumpLine(null)
  }

  return <section className="panel code-panel" aria-label="Canlı Python kodu">
    <div className="code-heading"><div><h2><Code2 size={20} />Canlı Kod <span>Python</span></h2><p>Seçilen plan: <strong>{selected}</strong><span>·</span>İzlenen çalışma: <strong>{trace.mission_id ?? 'Yok'}</strong><span>·</span>{STATUS_LABELS[trace.status ?? 'idle'] ?? trace.status}</p></div><div className="code-display-actions"><button className={'button button-quiet ' + (frozen ? 'display-frozen' : '')} aria-pressed={Boolean(frozen)} onClick={() => { setFrozen(previous => previous ? null : { trace: live.trace, history: live.history }); setInspected(null) }}>{frozen ? <Play size={15} /> : <Pause size={15} />}{frozen ? 'Ekranı Sürdür' : 'Ekranı Dondur'}</button><button className={'button ' + (autoFollow && !inspected ? 'button-primary' : 'button-quiet')} onClick={() => follow()}><LocateFixed size={15} />{blockView ? 'Canlı Bloğu İzle' : 'Canlı Satırı İzle'}</button></div></div>
    <div className={'teaching-block-banner ' + (blockActive && autoFollow ? 'is-active' : '')} style={blockStyle(bannerBlock)} data-testid="teaching-block-banner" data-block-id={bannerBlock?.id} data-block-name={bannerBlock?.label} data-block-active={Boolean(blockActive && autoFollow)}>
      <div className="teaching-block-symbol"><Layers3 size={21} /></div><div className="teaching-block-copy"><span>{sourceOnly ? 'Kaynak blokları' : bannerStatus}</span><strong aria-live="polite">{bannerBlock?.label ?? (sourceMatchesExecution ? 'İşlem Bekleniyor' : 'Kaynak Blokları')}</strong><p>{sourceOnly ? 'Bu dosya okunabilir; canlı yürütme izi alınmıyor.' : stale ? 'Bağlantı kesildi; son kaydın bloğu gösteriliyor.' : bannerBlock?.description ?? 'Gerçek kaynak yüklendiğinde kod bölümleri kısa adlar ve renklerle görünür.'}</p></div>
      <div className="teaching-block-location">{bannerBlock ? <span className="block-range">L{bannerBlock.startLine}–{bannerBlock.endLine}</span> : null}{displayed ? <><span>{inspected ? 'Geçmiş olay' : focus?.isCaller && blockView ? 'Alt çağrı' : 'Python konumu'}</span><strong>{getBlockLabel(displayed)}</strong><code>{displayed.function} · L{displayed.line ?? displayed.lineno}</code></> : <span>İz bekleniyor</span>}</div>
    </div>
    <div className="code-toolbar"><div className="trace-lanes" role="group" aria-label="İzleme hattı"><button className={lane === 'mission' ? 'selected' : ''} aria-pressed={lane === 'mission'} onClick={() => follow('mission')}>Görev</button><button className={lane === 'vision' ? 'selected' : ''} aria-pressed={lane === 'vision'} onClick={() => follow('vision')}>Görüntü işleme</button></div><div className="code-view-switch" role="group" aria-label="Kod görünümü"><button className={blockView ? 'selected' : ''} aria-pressed={blockView} onClick={() => changeView(true)}><Layers3 size={12} />Blok görünümü</button><button className={!blockView ? 'selected' : ''} aria-pressed={!blockView} onClick={() => changeView(false)}>Satır ayrıntısı</button></div><label>Dosya<select aria-label="Python dosyası" value={followedFile} onChange={event => { setFile(event.target.value); setInspected(null); setAutoFollow(false); setJumpLine(null) }}>{live.files.length ? live.files.map(item => <option key={item.file} value={item.file}>{item.file}{item.trace_enabled ? '' : ' · yalnız kaynak'}</option>) : <option value="control.py">control.py</option>}</select></label><label>İşlev<select aria-label="Python işlevi" value="" onChange={event => { setAutoFollow(false); setFile(followedFile); setInspected(null); setJumpLine(Number(event.target.value)) }}><option value="">{activeFunction?.name ?? 'İşleve git…'}</option>{source?.functions.map(fn => <option key={fn.name + ':' + fn.line} value={fn.line}>{fn.name} · L{fn.line}</option>)}</select></label><div className="code-font-controls" role="group" aria-label="Kod yazı boyutu"><button aria-label="Kod yazısını küçült" disabled={fontSize <= 12} onClick={() => setFontSize(size => Math.max(12, size - 2))}>A−</button><span aria-live="polite">{fontSize} px</span><button aria-label="Kod yazısını büyüt" disabled={fontSize >= 22} onClick={() => setFontSize(size => Math.min(22, size + 2))}>A+</button></div><span className={'trace-health ' + (liveLane ? 'live' : '')}><Radio size={12} />{frozen ? 'Ekran sabit' : stale ? 'Bağlantı yok' : liveLane ? 'Canlı iz' : 'Son çalışma'}</span></div>
    {frozen ? <div className="code-notice">Yalnız ekran donduruldu. Uçuş, Python yürütmesi ve kayıt arka planda sürer.</div> : null}
    {source?.source_changed ? <div className="code-notice warning"><TriangleAlert size={14} />Dosya diskte değişti. Gösterilen kod çalışma başlangıcındaki SHA ile eşleşir. Yeni kodu yüklemek için inişten sonra Python başlatıcı terminalini kapatıp Baslat.cmd ile yeniden açın; tarayıcıyı yenilemek ve Gazebo oturumunu durdurup başlatmak Python kodunu yenilemez.</div> : null}
    {live.error || sourceError ? <div className="code-notice warning">{live.error ?? sourceError}</div> : null}
    {navigationBlocks.length ? <nav className="teaching-block-nav" aria-label="Kod blokları"><span className="block-nav-label">Bloklara git</span><div ref={blockNavigation}>{navigationBlocks.map((block, index) => <button key={block.id} style={blockStyle(block)} className={(blockActive && liveBlock?.id === block.id ? 'active ' : '') + (!autoFollow && viewedBlock?.id === block.id ? 'selected' : '')} data-block-id={block.id} data-block-name={block.label} data-block-active={Boolean(blockActive && liveBlock?.id === block.id)} aria-label={block.label + ' bloğuna git'} onClick={() => jumpToBlock(block)}><span>{String(index + 1).padStart(2, '0')}</span><strong>{block.label}</strong>{blockActive && liveBlock?.id === block.id ? <i aria-label={frozen ? 'Dondurulan blok' : 'Çalışan blok'} /> : null}</button>)}</div></nav> : null}
    <div className="code-body"><div className="source-column"><div className="source-caption"><span><Braces size={13} />{source?.file ?? followedFile}<small>{source?.lines.length ?? 0} satır</small></span><span>{sourceOnly ? 'Yalnız kaynak · bu dosya izlenmiyor' : inspected ? 'Geçmiş olay inceleniyor' : stale ? 'Son kayıt · bağlantı yok' : callerLine ? 'Üst çağrı · L' + callerLine + ' · alt işlev çalışıyor' : actualLine ? 'Gerçek Python konumu · L' + actualLine : 'Henüz satır olayı yok'}</span></div><div className={'source-viewport ' + (stale ? 'trace-stale' : '')} style={{ '--code-font-size': fontSize + 'px', '--code-line-height': Math.round(fontSize * 1.85) + 'px' } as CSSProperties} ref={viewport} tabIndex={0} aria-label="Python kaynak satırları">{source ? rows.map(row => <div className="source-row-group" key={row.line}>{row.block?.startLine === row.line ? <div className={'source-block-heading ' + (blockActive && liveBlock?.id === row.block.id ? 'active' : '')} style={blockStyle(row.block)} data-block-id={row.block.id} data-block-start={row.line}><span className="source-block-marker" /><strong>{row.block.label}</strong><small>L{row.block.startLine}–{row.block.endLine}</small>{blockActive && liveBlock?.id === row.block.id ? <span className="source-block-state">{frozen ? 'Ekran sabit' : 'Bu blokta'}</span> : null}</div> : null}<SourceLine text={row.text} line={row.line} current={executionVisible && !callerLine && row.line === actualLine} caller={executionVisible && !inspected && row.line === callerLine} selected={row.line === inspectedLine} exception={current?.event === 'exception'} block={row.block} activeBlock={Boolean(blockActive && liveBlock?.id === row.block?.id)} /></div>) : <div className="code-empty"><Code2 size={30} /><strong>{loading ? 'Gerçek kaynak yükleniyor…' : 'Kaynak bekleniyor'}</strong><span>Kod, yerel servisin izin verilen Python dosyalarından okunur.</span></div>}</div><div className="source-footer"><span>SHA {source?.sha256?.slice(0, 12) ?? '—'}</span><span>{blockView ? 'Renkler kod bölümlerini ayırır; üst çağrı ile çalışan alt satır ayrı gösterilir.' : 'Satır olayı, satır çalıştırılmadan hemen önce kaydedilir.'}</span></div></div>
      <aside className="trace-inspector"><section className="execution-context">
        <div className="trace-section-heading"><h3>{inspected ? 'Seçilen olay' : stale ? 'Son kayıt' : 'Şimdi ne oluyor?'}</h3><span>{displayed?.event ? EVENT_LABELS[displayed.event] : 'Bekleniyor'}</span></div>
        {displayed ? <><strong className="execution-function">{getBlockLabel(displayed)} <span>L{displayed.line ?? displayed.lineno}</span></strong><code className="execution-raw-function">{displayed.function}</code><p>{stale && !inspected ? 'İz bağlantısı yok. Bu, son alınan yürütme konumudur; güncel koşul ölçümleri gizlendi.' : wait?.description ?? executionFunction?.explanation ?? displayed.phase ?? 'Gerçek Python yürütme konumu izleniyor.'}</p>
          {wait ? <><div className="wait-readout"><span>{wait.kind ?? 'Bekleme'}</span><span>{number(wait.elapsed_s, 1)} s{wait.timeout_s == null ? '' : ' / ' + number(wait.timeout_s, 0) + ' s'}</span></div>
            <dl className="wait-conditions">
              {typeof wait.distance_m === 'number' ? <div><dt>Hedefe yatay</dt><dd>{number(wait.distance_m, 2)} m</dd></div> : null}
              {typeof wait.altitude_error_m === 'number' ? <div><dt>İrtifa hatası</dt><dd>{number(wait.altitude_error_m, 2)} m</dd></div> : null}
              {typeof wait.speed_mps === 'number' ? <div><dt>Hız</dt><dd>{number(wait.speed_mps, 2)} m/s</dd></div> : null}
              {wait.goal_enu ? <div className="wait-goal"><dt>Hedef E/N/U</dt><dd>{wait.goal_enu.map(value => number(value, 1)).join(' / ')} m</dd></div> : null}
            </dl></> : null}
          <dl className="execution-readouts"><div><dt>Aşama</dt><dd>{phaseLabel}</dd></div><div><dt>Çalışma</dt><dd title={trace.run_id ?? undefined}>{trace.run_id ?? '—'}</dd></div><div><dt>Süre / kayıt yaşı</dt><dd>{duration(displayed.elapsed_s)} / {inspected ? 'geçmiş olay' : stale ? 'bağlantı yok' : number(current?.age_s, 1) + ' s'}</dd></div></dl>
          {displayed.event === 'exception' ? <div className="trace-exception"><TriangleAlert size={14} />Gerçek istisna: {displayed.exception_type ?? 'Python exception'}</div> : null}
        </> : <p>Bir görev çalıştığında gerçek dosya, işlev ve satır burada görünür. Kod ekranını açmak görevi başlatmaz.</p>}
      </section>
      <section className="call-stack"><div className="trace-section-heading"><h3>Çağrı yığını</h3></div>{inspected ? <p className="trace-empty-copy">Bu geçmiş olayda yığın kaydedilmedi.</p> : current?.stack?.length ? <ol>{current.stack.map((frame, index) => <li key={frame.file + ':' + frame.line + ':' + index}><button onClick={() => { setFile(frame.file); setAutoFollow(false); setInspected(null); setJumpLine(frame.line ?? frame.lineno ?? null) }}><span><strong>{getBlockLabel(frame)}</strong><small>{frame.function}</small></span><small>{frame.file}:{frame.line ?? frame.lineno}</small></button></li>)}</ol> : <p className="trace-empty-copy">Yığın kaydı bekleniyor.</p>}</section>
      <section className="trace-history"><div className="trace-section-heading"><h3><History size={14} />Son satır olayları</h3>{(trace.skipped ?? 0) + (trace.dropped ?? 0) > 0 ? <span title={'Yanıt sınırı: ' + (trace.skipped ?? 0) + '; tampon dışı: ' + (trace.dropped ?? 0)}>Örneklenmiş iz</span> : <span>{recent.length} olay</span>}</div><div className="trace-history-list">{recent.length ? recent.map(event => <button key={event.lane + ':' + event.seq} className={inspected?.seq === event.seq ? 'selected' : event.event === 'exception' ? 'exception' : ''} onClick={() => inspect(event)}><span className="trace-event-kind">{EVENT_LABELS[event.event]}</span><strong title={event.function}>{getBlockLabel(event)}</strong><small>L{event.line ?? event.lineno}</small></button>) : <p className="trace-empty-copy">Bu hat için henüz kayıt yok.</p>}</div></section>
      </aside></div>
  </section>
}
