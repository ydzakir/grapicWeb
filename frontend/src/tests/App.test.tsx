import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from '../App'

describe('App Shell Component', () => {
  it('renders application header title', () => {
    render(<App />)
    expect(screen.getByText('Infrastructure Monitoring & Auto-Topology')).toBeInTheDocument()
  })

  it('renders operational status banner', () => {
    render(<App />)
    expect(screen.getByText('● Operational')).toBeInTheDocument()
  })
})
