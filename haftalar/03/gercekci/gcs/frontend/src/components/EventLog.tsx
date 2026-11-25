import { CircleAlert, Download, Info, List, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { GcsEvent } from '../types'
import { eventTime } from '../format'

export function EventLog({ events, expanded = false }: { events: GcsEvent[]; expanded?: boolean }) {
  const [query, setQuery] = useState('')
  const rows = useMemo(() => {
    const stamp = (event: GcsEvent) => {
      if (typeof event.timestamp === 'number') return event.timestamp < 1e12 ? event.timestamp * 1000 : event.timestamp
      const parsed = Date.parse(event.timestamp ?? '')
      if (Number.isFinite(parsed)) return parsed
      const time = (event.time ?? event.timestamp ?? '').match(/^(\d\d):(\d\d):(\d\d)/)
      return time ? (+time[1] * 3600 + +time[2] * 60 + +time[3]) * 1000 : 0
    }
    return [...events].sort((a, b) => stamp(b) - stamp(a)).filter(e => !query || e.message.toLocaleLowerCase('tr').includes(query.toLocaleLowerCase('tr')))
  }, [events, query])
  const exportEvents = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(events, null, 2)], { type: 'application/json' }))
    const a = document.createElement('a'); a.href = url; a.download = `rota-gcs-olaylar-${new Date().toISOString().replaceAll(':', '-')}.json`; a.click(); URL.revokeObjectURL(url)
  }
  return <section className={`panel event-panel ${expanded ? 'expanded' : ''}`}>
    <div className="panel-heading event-heading"><h2><List size={21} />Olay Kayıtları</h2><div className="heading-tools">{expanded ? <label className="event-search"><Search size={16} /><input aria-label="Olaylarda ara" value={query} onChange={e => setQuery(e.target.value)} placeholder="Olaylarda ara" /></label> : null}<button className="icon-button subtle" title="Görünen olayları JSON olarak indir" aria-label="Olay kayıtlarını indir" disabled={!events.length} onClick={exportEvents}><Download size={17} /></button></div></div>
    <div className="event-scroll"><table><thead><tr><th title="En yeni olay önce">Saat</th><th>Seviye</th><th>Olay</th></tr></thead><tbody>{rows.length ? rows.map((event, index) => {
      const level = (event.level ?? 'info').toLowerCase()
      const warning = ['warning', 'warn', 'error', 'critical'].includes(level)
      return <tr key={event.id ?? `${event.timestamp}-${index}`}><td>{event.time ?? eventTime(event.timestamp)}</td><td className={warning ? 'log-warning' : 'log-info'}>{warning ? <CircleAlert size={15} /> : <Info size={15} />}<span>{level === 'error' || level === 'critical' ? 'HATA' : warning ? 'UYARI' : 'BİLGİ'}</span></td><td>{event.message}</td></tr>
    }) : <tr><td colSpan={3} className="empty-log">{query ? 'Bu aramayla eşleşen olay yok.' : 'Görev başladığında olaylar burada görüntülenecek.'}</td></tr>}</tbody></table></div>
    {expanded ? <div className="panel-footnote">{events.length} olay · Bu oturumdan alınan gerçek zamanlı kayıtlar</div> : null}
  </section>
}
