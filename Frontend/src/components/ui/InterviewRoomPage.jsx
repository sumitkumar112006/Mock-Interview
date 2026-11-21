import React, { useState } from 'react';
import { Orb } from '@yogesharc/thinking-orbs';
import ThinkingOrb from './ThinkingOrb';
import AudioTracker from './AudioTracker';
import './InterviewRoomPage.css';

export function InterviewRoomPage({
  session,
  activeQuestion,
  recording,
  seconds,
  formatTime,
  onStartRecording,
  onStopRecording,
  onRetryRecording,
  onNextQuestion,
  onFinishSession,
  onExit,
  evaluation = null,
  recordedAnswer = null,
  recordedAudioUrl = null,
  recordingError = null,
  isAnalyzing = false,
  onPlayAudio = null,
  isPlayingAudio = false,
  followupCount = 0,
}) {
  const [micMuted, setMicMuted] = useState(false);
  const [cameraOff, setCameraOff] = useState(false);

  // Compute reactive ThinkingOrb state
  const orbState = isAnalyzing
    ? 'thinking'
    : recording
    ? 'listening'
    : isPlayingAudio
    ? 'speaking'
    : 'idle';

  const roleTitle = session?.target_role || 'Software Engineer';
  const currentQNum = activeQuestion?.question_number || 1;
  const totalQuestions = session?.questions?.length || 5;

  const handlePrimaryClick = () => {
    if (isAnalyzing) return;
    if (recording) {
      onStopRecording();
    } else if (isPlayingAudio) {
      // Candidate wants to skip coach speaking and immediately record answer
      if (onPlayAudio) onPlayAudio();
      onStartRecording();
    } else {
      onStartRecording();
    }
  };

  return (
    <div className="interview-room-page">
      {/* Top Header */}
      <header className="room-header">
        <div className="room-brand">
          <button type="button" className="room-exit-btn" onClick={onExit} title="Exit to preparation dashboard">
            ← Exit to Setup
          </button>
          <div className="room-live-pill">
            <span style={{ display: 'inline-flex', alignItems: 'center', marginRight: '6px' }}>
              <Orb
                state={orbState === 'listening' ? 'using' : (orbState === 'speaking' ? 'working' : (orbState === 'thinking' ? 'reasoning' : 'idle'))}
                variant={orbState === 'listening' ? 'record' : (orbState === 'speaking' ? 'gyro' : (orbState === 'thinking' ? 'twins' : 'blink'))}
                size={14}
              />
            </span>
            LIVE INTERVIEW
          </div>
        </div>

        <div className="room-center-meta">
          <span>Role: <strong>{roleTitle}</strong></span>
          <span>•</span>
          <span>Question <strong>{currentQNum}</strong> of {totalQuestions}</span>
          {(followupCount > 0 || activeQuestion?.is_followup) && (
            <>
              <span>•</span>
              <span style={{ color: '#fbbf24', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                ⚡ Follow-up {followupCount || 1} of 2
              </span>
            </>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="room-timer" title="Elapsed interview time">
            ⏱ {formatTime(seconds)}
          </div>
          <button type="button" className="room-exit-btn" onClick={onFinishSession} style={{ color: '#f87171' }}>
            Finish Interview ✕
          </button>
        </div>
      </header>

      {/* Main Studio Body */}
      <main className="room-body">
        {/* Left: Camera Stage with Bottom-Middle Thinking Orb */}
        <section className="room-camera-stage">
          <div className="stage-topbar">
            <span className="stage-tag">CAM 01 • DUMMY PREVIEW</span>
            <span className="stage-status" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <Orb
                state={recording ? 'using' : (isPlayingAudio ? 'working' : (isAnalyzing ? 'reasoning' : 'idle'))}
                variant={recording ? 'record' : (isPlayingAudio ? 'gyro' : (isAnalyzing ? 'twins' : 'default'))}
                size={14}
              />
              {recording
                ? 'RECORDING CANDIDATE AUDIO'
                : (isPlayingAudio
                    ? (activeQuestion?.is_followup ? 'AI COACH ASKING FOLLOW-UP' : 'AI COACH ASKING QUESTION')
                    : (isAnalyzing ? 'ANALYZING CANDIDATE ANSWER' : 'AUDIO READY • YOUR TURN'))}
            </span>
          </div>

          {/* Dummy Camera Viewport */}
          <div className="dummy-camera-viewport">
            <div className="dummy-silhouette" style={{ opacity: cameraOff ? 0.15 : 0.45 }}>
              <div className="dummy-head" />
              <div className="dummy-torso" />
            </div>

            <div className="dummy-watermark">
              <strong>Candidate Stage</strong><br />
              <span>Camera dummy view active (no hardware permission required)</span>
            </div>

            {/* Bottom-Middle Thinking Orb (Official @yogesharc/thinking-orbs) */}
            <div className="stage-orb-dock">
              <ThinkingOrb state={orbState} size={52} />
            </div>
          </div>
        </section>

        {/* Right: Question Details & Live Evaluation */}
        <aside className="room-sidebar-panel">
          <div className="room-question-card">
            <div className="room-card-top">
              {activeQuestion?.is_followup ? (
                <span className="round-chip" style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.4)', fontWeight: 700 }}>
                  ⚡ Follow-up {followupCount || 1} of 2
                </span>
              ) : (
                <span className="round-chip">
                  {activeQuestion?.round_name || activeQuestion?.category || 'Technical Core'}
                </span>
              )}

              {onPlayAudio && (
                <button
                  type="button"
                  className={`read-aloud-btn ${isPlayingAudio ? 'speaking' : ''}`}
                  onClick={onPlayAudio}
                  title={isPlayingAudio ? "Click to stop speaking" : "Read question aloud"}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  {isPlayingAudio ? (
                    <>
                      <Orb state="working" variant="gyro" size={14} />
                      Stop Audio
                    </>
                  ) : (
                    <>
                      <span>🔈</span> Read Aloud
                    </>
                  )}
                </button>
              )}
            </div>

            {activeQuestion?.is_followup && activeQuestion?.original_question_text && (
              <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '8px', lineHeight: '1.4' }}>
                ↳ Follow-up to: <em>"{activeQuestion.original_question_text}"</em>
              </div>
            )}

            <h2>{activeQuestion?.question_text || activeQuestion?.title || 'Tell me about yourself.'}</h2>
            <p>{activeQuestion?.intent || activeQuestion?.detail || 'A concise story connecting your past, present, and next steps.'}</p>

            {/* Conversational AI Coach / Candidate Status Prompt Banner */}
            {isPlayingAudio && (
              <div
                className="coach-speaking-prompt-banner"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  background: 'rgba(251, 191, 36, 0.1)',
                  border: '1px solid rgba(251, 191, 36, 0.35)',
                  borderRadius: '10px',
                  padding: '10px 14px',
                  margin: '4px 0 10px 0',
                  color: '#fef08a',
                  fontSize: '12.5px',
                  lineHeight: '1.45',
                }}
              >
                <Orb state="working" variant="gyro" size={18} />
                <span>
                  <strong>AI Coach is asking the question aloud...</strong> Listen carefully, or click <em>"Skip & Record"</em> below to start speaking immediately.
                </span>
              </div>
            )}

            {!isPlayingAudio && !recording && !recordedAnswer && !isAnalyzing && (
              <div
                className="candidate-turn-prompt-banner"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  background: 'rgba(167, 139, 250, 0.1)',
                  border: '1px solid rgba(167, 139, 250, 0.3)',
                  borderRadius: '10px',
                  padding: '10px 14px',
                  margin: '4px 0 10px 0',
                  color: '#e2d9f3',
                  fontSize: '12.5px',
                  lineHeight: '1.45',
                }}
              >
                <Orb state="idle" variant="default" size={16} />
                <span>
                  <strong>Your turn:</strong> Click <strong>"Record Answer"</strong> below and speak your response into your microphone.
                </span>
              </div>
            )}

            {/* Recording & Transcription Error Alert Box with Retry */}
            {recordingError && (
              <div
                className="recording-error-box"
                style={{
                  background: 'rgba(239, 68, 68, 0.12)',
                  border: '1px solid rgba(239, 68, 68, 0.45)',
                  borderRadius: '8px',
                  padding: '12px 14px',
                  margin: '14px 0',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171', fontWeight: 600, fontSize: '13px' }}>
                  <span>⚠️ Audio Capture / Transcription Error</span>
                </div>
                <p style={{ color: '#fecaca', fontSize: '12.5px', margin: '6px 0 10px 0', lineHeight: 1.45 }}>
                  {recordingError}
                </p>
                {onRetryRecording && (
                  <button
                    type="button"
                    onClick={onRetryRecording}
                    style={{
                      background: 'rgba(239, 68, 68, 0.25)',
                      border: '1px solid #f87171',
                      color: '#fff',
                      borderRadius: '6px',
                      padding: '5px 12px',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                    }}
                  >
                    <span>↺</span> Retry Recording
                  </button>
                )}
              </div>
            )}

            {/* Candidate Spoken Answer Transcript */}
            {recordedAnswer && (
              <div
                className="candidate-transcript-box"
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: `1px solid ${recordedAnswer.startsWith('(') ? 'rgba(244, 63, 94, 0.35)' : 'rgba(167, 139, 250, 0.3)'}`,
                  borderRadius: '8px',
                  padding: '10px 14px',
                  margin: '12px 0',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#c4b5fd', fontWeight: 600, marginBottom: '4px' }}>
                  <span>🎙️ Your Spoken Answer (Transcribed by Groq Whisper):</span>
                </div>
                <p style={{
                  fontStyle: recordedAnswer.startsWith('(') ? 'italic' : 'normal',
                  color: recordedAnswer.startsWith('(') ? '#fca5a5' : '#f5f3ff',
                  fontSize: '13px',
                  lineHeight: '1.5',
                  margin: 0,
                }}>
                  {recordedAnswer}
                </p>

                {/* Interactive Audio Tracker Player */}
                {recordedAudioUrl && (
                  <AudioTracker audioUrl={recordedAudioUrl} />
                )}
              </div>
            )}

            {/* Live Evaluation Box with Thinking Orbs */}
            {isAnalyzing && (
              <div className="evaluation-feedback-box" style={{ borderLeftColor: '#38bdf8' }}>
                <div className="eval-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Orb state="reasoning" variant="twins" size={20} />
                  <strong>AI Evaluation in progress... ⏳</strong>
                </div>
                <div className="eval-feedback-text">
                  Analyzing candidate response for STAR structure, technical depth, and speaking cadence.
                </div>
              </div>
            )}

            {evaluation && !isAnalyzing && (
              <div className="evaluation-feedback-box">
                <div className="eval-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Orb state="compacting" variant="fuse" size={20} />
                  <strong>Answer Evaluation</strong>
                  <span className="eval-score-badge" style={{ marginLeft: 'auto' }}>Score: {evaluation.score}/100</span>
                </div>
                <div className="eval-feedback-text">
                  {evaluation.feedback}
                </div>
                {evaluation.suggested_followup && (
                  <div className="eval-followup">
                    <strong>Suggested Follow-up:</strong> "{evaluation.suggested_followup}"
                  </div>
                )}
              </div>
            )}
          </div>
        </aside>
      </main>

      {/* Bottom Floating Controls Dock */}
      <footer className="room-bottom-dock">
        <div className="dock-left">
          <button
            type="button"
            className={`dock-circle-btn ${micMuted ? 'muted' : ''}`}
            onClick={() => setMicMuted(!micMuted)}
            title={micMuted ? 'Unmute Mic' : 'Mute Mic'}
          >
            {micMuted ? '🔇' : '🎙️'}
          </button>
          <button
            type="button"
            className={`dock-circle-btn ${cameraOff ? 'muted' : ''}`}
            onClick={() => setCameraOff(!cameraOff)}
            title={cameraOff ? 'Enable Camera' : 'Disable Camera'}
          >
            {cameraOff ? '🚫' : '📷'}
          </button>
        </div>

        <div className="dock-center">
          <button
            type="button"
            className={`dock-primary-btn ${recording ? 'recording' : (isPlayingAudio ? 'coach-speaking' : '')}`}
            onClick={handlePrimaryClick}
            disabled={isAnalyzing}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '10px',
              opacity: isAnalyzing ? 0.8 : 1,
              cursor: isAnalyzing ? 'not-allowed' : 'pointer'
            }}
          >
            {isAnalyzing ? (
              <>
                <Orb state="reasoning" variant="twins" size={18} />
                Transcribing & Scoring... ⏳
              </>
            ) : recording ? (
              <>
                <Orb state="using" variant="record" size={18} />
                Stop & Submit Answer
              </>
            ) : isPlayingAudio ? (
              <>
                <Orb state="working" variant="gyro" size={18} />
                Coach Speaking... (Skip & Record)
              </>
            ) : (
              <>
                <Orb state="idle" variant="default" size={18} />
                Record Answer
              </>
            )}
          </button>
        </div>

        <div className="dock-right">
          <button type="button" className="dock-secondary-btn" onClick={onNextQuestion}>
            Next Question ↗
          </button>
        </div>
      </footer>
    </div>
  );
}

export default InterviewRoomPage;
