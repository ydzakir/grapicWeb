export default function App() {
  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <header style={{ borderBottom: '1px solid #334155', paddingBottom: '1rem', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 'bold', margin: 0, color: '#38bdf8' }}>
          Infrastructure Monitoring &amp; Auto-Topology
        </h1>
        <p style={{ color: '#94a3b8', marginTop: '0.5rem' }}>
          MVP Dashboard Shell - Real-time Infrastructure Monitoring
        </p>
      </header>

      <main style={{ background: '#1e293b', borderRadius: '8px', padding: '1.5rem', border: '1px solid #334155' }}>
        <h2 style={{ fontSize: '1.25rem', marginTop: 0 }}>System Shell Ready</h2>
        <p style={{ color: '#cbd5e1' }}>
          Backend REST &amp; WebSocket endpoint ready via reverse proxy.
        </p>
        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
          <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '6px', flex: 1, border: '1px solid #334155' }}>
            <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Status</span>
            <div style={{ color: '#10b981', fontWeight: 'bold', fontSize: '1.125rem', marginTop: '0.25rem' }}>
              ● Operational
            </div>
          </div>
          <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '6px', flex: 1, border: '1px solid #334155' }}>
            <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Environment</span>
            <div style={{ color: '#f8fafc', fontWeight: 'bold', fontSize: '1.125rem', marginTop: '0.25rem' }}>
              Development / Docker
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
