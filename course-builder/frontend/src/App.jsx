import React, { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'

const PHASES = [
  { id: 1, name: 'Terrain Creation', gate: 'terrain_ready', tool: 'lidar_mcp' },
  { id: 2, name: 'Course Tracing (Phase1a)', gate: 'svg_complete', tool: 'phase1a_mcp' },
  { id: 3, name: 'Terrain Refinement', gate: 'terrain_exported', tool: 'unity_terrain_mcp' },
  { id: 4, name: 'SVG Conversion', gate: 'svg_converted', tool: 'svg_convert_mcp' },
  { id: 5, name: 'Blender Processing', gate: 'fbx_exported', tool: 'blender_mcp' },
  { id: 6, name: 'Unity Assembly', gate: 'course_complete', tool: 'unity_assembly_mcp' },
]

const QUICK_ACTIONS = [
  'Create new course',
  'Show workflow status',
  'Run Phase1a pipeline',
  'Generate SAM masks',
  'Export FBX files',
  'Build asset bundle'
]

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `# Welcome to Golf Course Builder! 🏌️

I'll help you build a complete GSPro golf course using the **"None to Done"** workflow.

**6 Phases:**
1. **Terrain Creation** - LIDAR to heightmap
2. **Course Tracing** - Phase1a SAM-based SVG generation
3. **Terrain Refinement** - Unity terrain adjustment
4. **SVG Conversion** - GSProSVGConvert
5. **Blender Processing** - Mesh conversion and export
6. **Unity Assembly** - Final asset bundle

To begin, say **"create new course"** with a name like: \`create new course "Pine Valley"\``
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [currentPhase, setCurrentPhase] = useState(1)
  const [courseInfo, setCourseInfo] = useState(null)
  const [tools, setTools] = useState({})
  const messagesEndRef = useRef(null)

  useEffect(() => {
    // Create session on mount
    createSession()
    // Fetch tools
    fetchTools()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const createSession = async () => {
    try {
      const res = await fetch('/api/chat/session', { method: 'POST' })
      const data = await res.json()
      setSessionId(data.sessionId)
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }

  const fetchTools = async () => {
    try {
      const res = await fetch('/api/chat/tools/hierarchy')
      const data = await res.json()
      setTools(data)
    } catch (err) {
      console.error('Failed to fetch tools:', err)
    }
  }

  const sendMessage = async (text = input) => {
    if (!text.trim() || loading) return

    const userMessage = { role: 'user', content: text }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId, message: text })
      })
      const data = await res.json()

      const assistantMessage = {
        role: 'assistant',
        content: data.message,
        toolInvocations: data.toolInvocations,
        suggestedNextStep: data.suggestedNextStep
      }
      setMessages(prev => [...prev, assistantMessage])

      // Update course info if available
      if (data.message.includes('Course ID:')) {
        const match = data.message.match(/Course ID: `([^`]+)`/)
        if (match) {
          setCourseInfo({ id: match[1] })
        }
      }

      // Check for gate completions to update phase
      if (data.toolInvocations) {
        data.toolInvocations.forEach(inv => {
          if (inv.output?.gateCompleted) {
            const phaseIndex = PHASES.findIndex(p => p.gate === inv.output.gateCompleted)
            if (phaseIndex >= 0 && phaseIndex + 1 > currentPhase) {
              setCurrentPhase(phaseIndex + 2) // Move to next phase
            }
          }
        })
      }
    } catch (err) {
      console.error('Failed to send message:', err)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="app">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h1>⛳ Course Builder</h1>
          <p>GSPro "None to Done" Workflow</p>
        </div>

        <div className="workflow-progress">
          <h3>Workflow Phases</h3>
          <ul className="phase-list">
            {PHASES.map((phase, idx) => (
              <li 
                key={phase.id} 
                className={`phase-item ${idx + 1 === currentPhase ? 'active' : ''} ${idx + 1 < currentPhase ? 'completed' : ''}`}
              >
                <span className="phase-icon">
                  {idx + 1 < currentPhase ? '✓' : idx + 1}
                </span>
                {phase.name}
              </li>
            ))}
          </ul>
        </div>

        {courseInfo && (
          <div style={{ padding: '20px', borderTop: '1px solid var(--border)' }}>
            <h3 style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Current Course
            </h3>
            <p style={{ fontSize: '0.85rem' }}>{courseInfo.name || 'Unnamed'}</p>
            <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{courseInfo.id}</p>
          </div>
        )}
      </div>

      {/* Main Chat Area */}
      <div className="main">
        <div className="chat-header">
          <h2>Golf Course Builder Chat</h2>
          <span className="course-info">
            Phase {currentPhase}/6: {PHASES[currentPhase - 1]?.name}
          </span>
        </div>

        <div className="chat-messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-content">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
                
                {msg.toolInvocations && msg.toolInvocations.length > 0 && (
                  <div className="tool-invocations">
                    <small style={{ color: 'var(--text-secondary)' }}>Tools executed:</small>
                    {msg.toolInvocations.map((inv, i) => (
                      <div key={i} className="tool-invocation">
                        <span className="tool-name">{inv.toolName}</span>
                        {inv.output?.gateCompleted && (
                          <span style={{ marginLeft: '8px', color: 'var(--success)' }}>
                            ✓ Gate: {inv.output.gateCompleted}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {loading && (
            <div className="message assistant">
              <div className="message-content">
                <span style={{ opacity: 0.7 }}>Thinking...</span>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-container">
          <div className="chat-input-wrapper">
            <input
              type="text"
              className="chat-input"
              placeholder="Tell me what you want to do with your golf course..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={loading}
            />
            <button 
              className="send-button" 
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
            >
              Send
            </button>
          </div>

          <div className="quick-actions">
            {QUICK_ACTIONS.map((action, idx) => (
              <button 
                key={idx} 
                className="quick-action"
                onClick={() => sendMessage(action)}
                disabled={loading}
              >
                {action}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tools Panel */}
      <div className="tools-panel">
        <h3>Available Tools</h3>
        
        {Array.isArray(tools) && tools.map((tool, idx) => (
          <div key={idx} className="tool-category">
            <div className="tool-item" onClick={() => sendMessage(`Use ${tool.name}`)}>
              <div className="tool-item-name">
                {tool.name}
                {tool.isMatryoshka && <span className="matryoshka-badge">MATRYOSHKA</span>}
              </div>
              <div className="tool-item-desc">
                {tool.description?.substring(0, 60)}...
              </div>
            </div>
            
            {tool.children && tool.children.map((child, cidx) => (
              <div 
                key={cidx} 
                className="tool-item" 
                style={{ marginLeft: '12px', background: 'var(--bg-primary)' }}
                onClick={() => sendMessage(`Use ${child.name}`)}
              >
                <div className="tool-item-name" style={{ fontSize: '0.8rem' }}>
                  {child.name}
                  {child.isMatryoshka && <span className="matryoshka-badge">+</span>}
                </div>
              </div>
            ))}
          </div>
        ))}
        
        {!Array.isArray(tools) || tools.length === 0 && (
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Loading tools...
          </p>
        )}
      </div>
    </div>
  )
}

export default App
