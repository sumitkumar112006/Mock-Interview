import { useEffect, useRef, useState } from 'react'
import {
  CameraPreviewCard,
  PromptCard,
  JobDescriptionModal,
  InterviewRoomPage,
} from './components/ui'
import {
  uploadJobDescription,
  uploadResume,
  startInterviewSession,
  getNextQuestion,
  submitAnswer,
  endInterview,
  transcribeAudio,
  synthesizeSpeech,
} from './services/api'
import './App.css'

const fallbackQuestions = [
  { question_number: 1, round_name: 'Technical Core', question_text: 'Can you walk me through the architecture of a complex application you designed or contributed to? How did data flow between the frontend and backend?', intent: 'Assess system comprehension, component modularity, and API design.', time_limit_minutes: 3 },
  { question_number: 2, round_name: 'Technical Deep-Dive', question_text: 'Describe a specific performance bottleneck or latency issue you encountered. What tools did you use to diagnose it, and how did you resolve it?', intent: 'Evaluate diagnostic ability, profiling, and optimization techniques.', time_limit_minutes: 3 },
  { question_number: 3, round_name: 'Behavioral & STAR', question_text: 'Tell me about a time you had a technical disagreement with a team member or stakeholder. How did you handle the situation and what was the outcome?', intent: 'Evaluate STAR framework delivery, empathy, compromise, and professional maturity.', time_limit_minutes: 3 },
  { question_number: 4, round_name: 'System Design', question_text: 'How do you handle graceful degradation and failure modes when an external third-party service or database fails in your system?', intent: 'Check fault tolerance, circuit breakers, retry backoff, and fallback UI.', time_limit_minutes: 4 },
]

const navItems = [
  { id: 'interview', icon: '◉', label: 'Interview room' },
]

function App() {
  const [isInInterviewRoom, setIsInInterviewRoom] = useState(false)
  const [session, setSession] = useState(null)
  const [activeQuestion, setActiveQuestion] = useState(fallbackQuestions[0])
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [completed, setCompleted] = useState(() => Number(localStorage.getItem('prep-completed') || 0))
  const [showToast, setShowToast] = useState(false)
  const [toastMessage, setToastMessage] = useState('')
  const [micEnabled, setMicEnabled] = useState(true)
  const [cameraEnabled, setCameraEnabled] = useState(false)
  const [isScheduling, setIsScheduling] = useState(false)
  const [jobDescription, setJobDescription] = useState('')
  const [jdFile, setJdFile] = useState(null)
  const [resumeFile, setResumeFile] = useState(null)
  const [resumeText, setResumeText] = useState('')
  const [isSettingUp, setIsSettingUp] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [evaluation, setEvaluation] = useState(null)
  const [recordedAnswer, setRecordedAnswer] = useState(null)
  const [recordedAudioUrl, setRecordedAudioUrl] = useState(null)
  const [recordingError, setRecordingError] = useState(null)
  const [isPlayingAudio, setIsPlayingAudio] = useState(false)
  const [followupCount, setFollowupCount] = useState(0)

  const mediaRecorderRef = useRef(null)
  const micStreamRef = useRef(null)
  const audioChunksRef = useRef([])
  const audioPlayerRef = useRef(null)
  const recordedAudioUrlRef = useRef(null)
  const activeUtteranceRef = useRef(null)
  const lastSpokenQuestionKeyRef = useRef(null)
  const [browserVoices, setBrowserVoices] = useState([])

  // Load and cache browser speech synthesis voices
  useEffect(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      const loadVoices = () => {
        const v = window.speechSynthesis.getVoices()
        if (v && v.length > 0) {
          setBrowserVoices(v)
        }
      }
      loadVoices()
      window.speechSynthesis.onvoiceschanged = loadVoices
      return () => {
        if (window.speechSynthesis) {
          window.speechSynthesis.onvoiceschanged = null
        }
      }
    }
  }, [])

  // Auto-play question audio when candidate enters the interview room or switches questions
  useEffect(() => {
    if (!isInInterviewRoom || !activeQuestion) {
      lastSpokenQuestionKeyRef.current = null
      stopAllQuestionAudio()
      return
    }

    // Do not re-trigger auto-play if this is a follow-up (it is spoken conversationally upon evaluation)
    if (activeQuestion.is_followup) {
      return
    }

    const qKey = `${activeQuestion.question_id || activeQuestion.question_number || 'q'}_${activeQuestion.question_text || activeQuestion.title}`

    // Only speak automatically if this specific question has not been spoken yet
    if (lastSpokenQuestionKeyRef.current !== qKey) {
      lastSpokenQuestionKeyRef.current = qKey

      // 400ms delay to let the interview room DOM and animations mount smoothly
      const timer = setTimeout(() => {
        handlePlayQuestionAudio()
      }, 400)
      return () => clearTimeout(timer)
    }
  }, [isInInterviewRoom, activeQuestion?.question_number, activeQuestion?.question_id, activeQuestion?.question_text, activeQuestion?.is_followup])

  // Timer while recording
  useEffect(() => {
    if (!recording) return undefined
    const timer = window.setInterval(() => setSeconds((value) => value + 1), 1000)
    return () => window.clearInterval(timer)
  }, [recording])

  // Step 1: Open Schedule Modal
  const handleOpenScheduleModal = () => {
    setIsScheduling(true)
  }

  // Step 2: Process JD & Resume through backend tool calls, then navigate to actual interview room
  const handleProcessAndEnterInterviewRoom = async () => {
    setIsSettingUp(true)
    try {
      // 1. Upload Job Description (File or Text)
      if (jdFile || jobDescription) {
        try {
          await uploadJobDescription({ file: jdFile, text: jobDescription })
        } catch (e) {
          console.warn('JD processing note:', e)
        }
      }

      // 2. Upload Candidate Resume (File or Text)
      if (resumeFile || resumeText) {
        try {
          await uploadResume({ file: resumeFile, text: resumeText })
        } catch (e) {
          console.warn('Resume processing note:', e)
        }
      }

      // 3. Tool call to initialize interview session & generate calibrated plan
      const newSession = await startInterviewSession({
        planOrRole: jobDescription ? 'Tailored Job Role' : 'Software Engineer',
      })

      setSession(newSession)
      if (newSession.questions && newSession.questions.length > 0) {
        setActiveQuestion(newSession.questions[0])
      } else {
        setActiveQuestion(fallbackQuestions[0])
      }

      // 4. Navigate into the actual interview room page
      setIsScheduling(false)
      setIsInInterviewRoom(true)
      setToastMessage('🎉 Entered Live Interview Room! Your questions are ready.')
      setShowToast(true)
      window.setTimeout(() => setShowToast(false), 3500)
    } catch (err) {
      console.warn('Backend interview start fallback, loading interview room with calibrated questions:', err)
      setIsScheduling(false)
      setActiveQuestion(fallbackQuestions[0])
      setIsInInterviewRoom(true)
      setToastMessage('Entered Live Interview Room. Ready to practice.')
      setShowToast(true)
      window.setTimeout(() => setShowToast(false), 3000)
    } finally {
      setIsSettingUp(false)
    }
  }

  // Audio Recording (Audio-only via MediaRecorder with Promise-awaited onstop lifecycle)
  const startAudioRecording = async () => {
    stopAllQuestionAudio()
    setRecordingError(null)
    setEvaluation(null)
    setRecordedAnswer(null)
    if (recordedAudioUrlRef.current) {
      URL.revokeObjectURL(recordedAudioUrlRef.current)
      recordedAudioUrlRef.current = null
    }
    setRecordedAudioUrl(null)
    setSeconds(0)
    audioChunksRef.current = []

    // 1. Check browser mediaDevices support (requires localhost or HTTPS)
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      const msg = 'Microphone access is not supported in this browser, or the page is not served over localhost/HTTPS.'
      console.error(msg)
      setRecordingError(msg)
      return
    }

    try {
      // 2. Request microphone with hardware-level acoustic filters
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      })
      micStreamRef.current = stream

      // 3. Detect supported MIME type in strict prioritized order
      let selectedMime = ''
      if (typeof MediaRecorder.isTypeSupported === 'function') {
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
          selectedMime = 'audio/webm;codecs=opus'
        } else if (MediaRecorder.isTypeSupported('audio/webm')) {
          selectedMime = 'audio/webm'
        } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
          selectedMime = 'audio/mp4'
        } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
          selectedMime = 'audio/ogg;codecs=opus'
        }
      }

      console.log(`🎙️ [RECORDER INIT] Selected MIME type: "${selectedMime || 'browser default'}"`)
      const recorder = selectedMime
        ? new MediaRecorder(stream, { mimeType: selectedMime })
        : new MediaRecorder(stream)

      mediaRecorderRef.current = recorder

      // 4. Continuously collect incoming audio chunks into ref (avoids stale closures)
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      recorder.onerror = (event) => {
        console.error('MediaRecorder runtime error:', event.error)
        setRecordingError(`Recording error: ${event.error?.message || 'Hardware capture error'}`)
        setRecording(false)
      }

      // 5. Start with 250ms timeslice to ensure continuous buffer filling
      recorder.start(250)
      setRecording(true)
    } catch (err) {
      console.error('Microphone acquisition error:', err)
      setRecording(false)

      let userMsg = 'Microphone access failed.'
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        userMsg = 'Microphone permission was denied. Please allow microphone permissions in your browser URL bar and try again.'
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        userMsg = 'No microphone device was detected on your system. Please connect a microphone and reload.'
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        userMsg = 'Your microphone is already in use by another application. Please close other audio apps and try again.'
      } else if (err.message) {
        userMsg = `Microphone error: ${err.message}`
      }

      setRecordingError(userMsg)
    }
  }

  // Promise-awaited stop function guaranteeing the Blob is built inside onstop
  const stopAudioRecording = async () => {
    const recorder = mediaRecorderRef.current
    const stream = micStreamRef.current

    if (!recorder || recorder.state === 'inactive') {
      setRecording(false)
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
        micStreamRef.current = null
      }
      return
    }

    setRecording(false)

    try {
      // 1. Await final Blob built inside recorder.onstop
      const audioBlob = await new Promise((resolve) => {
        recorder.onstop = () => {
          // Immediately stop ALL hardware microphone tracks so browser mic indicator turns off
          if (stream) {
            stream.getTracks().forEach((track) => track.stop())
            micStreamRef.current = null
          }

          const actualMime = recorder.mimeType || 'audio/webm'
          const blob = new Blob(audioChunksRef.current, { type: actualMime })
          resolve(blob)
        }

        recorder.stop()
      })

      console.log(`🎙️ [BLOB BUILT] Size: ${audioBlob.size} bytes | Type: ${audioBlob.type}`)

      // 2. Reject blobs under ~1KB (1024 bytes) with a clear user message
      if (audioBlob.size < 1024) {
        const errorMsg = 'Audio recording was too brief or silent (less than 1KB). Please hold your microphone and speak clearly for at least 3-5 seconds.'
        console.warn(errorMsg)
        setRecordingError(errorMsg)
        return
      }

      // 3. Create audio tracker URL so candidate can play and listen back to their recorded voice
      if (recordedAudioUrlRef.current) {
        URL.revokeObjectURL(recordedAudioUrlRef.current)
      }
      const audioUrl = URL.createObjectURL(audioBlob)
      recordedAudioUrlRef.current = audioUrl
      setRecordedAudioUrl(audioUrl)

      // 4. Process candidate answer and transcribe with Groq Whisper
      await processCandidateAnswer(audioBlob)
    } catch (err) {
      console.error('Failed to finalize audio recording:', err)
      setRecordingError(`Recording finalization failed: ${err.message}`)
    }
  }

  // Answer Processing & STAR Evaluation
  const processCandidateAnswer = async (audioBlob) => {
    setIsAnalyzing(true)
    setRecordingError(null)

    try {
      console.log(`📤 Uploading audio blob (${audioBlob.size} bytes, ${audioBlob.type}) to /api/v1/voice/transcribe...`)
      const transResult = await transcribeAudio(audioBlob)
      const transcriptText = (transResult?.transcript || transResult?.text || '').trim()

      console.log(`✨ [TRANSCRIPT RECEIVED]: "${transcriptText}"`)

      if (!transcriptText) {
        setRecordingError('No spoken words could be recognized from the audio. Please check your mic volume and try again.')
        setIsAnalyzing(false)
        return
      }

      setRecordedAnswer(transcriptText)

      // Submit real transcribed answer to STAR evaluation
      if (session && session.session_id) {
        const evalRes = await submitAnswer(session.session_id, {
          questionId: activeQuestion.question_id || 'q_1',
          questionText: activeQuestion.question_text || activeQuestion.title,
          answerText: transcriptText,
          expectedPoints: activeQuestion.expected_points || [],
        })
        setEvaluation(evalRes)

        // Responsiveness: AI Coach speaks evaluation result + follow-up question
        await handleSpeakEvaluationAndFollowup(evalRes)
      }
    } catch (err) {
      console.error('Transcription API failure:', err)
      setRecordingError(err.message || 'Groq Whisper transcription failed. Check backend connection.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleRetryRecording = () => {
    setRecordingError(null)
    setRecordedAnswer(null)
    if (recordedAudioUrlRef.current) {
      URL.revokeObjectURL(recordedAudioUrlRef.current)
      recordedAudioUrlRef.current = null
    }
    setRecordedAudioUrl(null)
    setEvaluation(null)
    startAudioRecording()
  }

  // Select best available English voice from browser synthesis engine
  const getBestEnglishVoice = () => {
    const list = browserVoices.length > 0
      ? browserVoices
      : (typeof window !== 'undefined' && 'speechSynthesis' in window ? window.speechSynthesis.getVoices() : [])
    if (!list || list.length === 0) return null

    // 1. Natural / Online high quality English voices (Edge / Windows 11 / Chrome)
    const naturalVoice = list.find((v) => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Online')))
    if (naturalVoice) return naturalVoice

    // 2. High-profile US English neural voices
    const namedVoice = list.find((v) =>
      v.lang.startsWith('en') &&
      (v.name.includes('Jenny') || v.name.includes('Aria') || v.name.includes('Google') || v.name.includes('Zira') || v.name.includes('Samantha') || v.name.includes('David'))
    )
    if (namedVoice) return namedVoice

    // 3. Any English voice
    const anyEn = list.find((v) => v.lang.startsWith('en') || v.lang.startsWith('en-') || v.lang.startsWith('en_'))
    if (anyEn) return anyEn

    return list[0]
  }

  // Stop any active audio / speech immediately
  const stopAllQuestionAudio = () => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause()
      audioPlayerRef.current.currentTime = 0
      audioPlayerRef.current = null
    }
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
    if (activeUtteranceRef.current) {
      activeUtteranceRef.current = null
    }
    window.__activeUtterance = null
    setIsPlayingAudio(false)
  }

  // Play interviewer speech using browser Web Speech API (zero-latency, natural tone)
  const speakWithBrowserWebSpeech = (text, onEndCallback = null) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setIsPlayingAudio(false)
      if (onEndCallback) onEndCallback()
      return
    }

    try {
      window.speechSynthesis.cancel()
      window.speechSynthesis.resume()

      const utterance = new SpeechSynthesisUtterance(text)
      activeUtteranceRef.current = utterance
      window.__activeUtterance = utterance // Chrome garbage collection safeguard

      const selectedVoice = getBestEnglishVoice()
      if (selectedVoice) {
        utterance.voice = selectedVoice
      }

      utterance.rate = 0.96
      utterance.pitch = 1.0

      utterance.onstart = () => {
        console.log('🗣️ [TTS] AI Coach started speaking:', text.slice(0, 60) + '...')
        setIsPlayingAudio(true)
      }

      utterance.onend = () => {
        console.log('✅ [TTS] AI Coach finished speaking.')
        setIsPlayingAudio(false)
        activeUtteranceRef.current = null
        window.__activeUtterance = null
        if (onEndCallback) onEndCallback()
      }

      utterance.onerror = (e) => {
        console.warn('SpeechSynthesis error:', e)
        setIsPlayingAudio(false)
        activeUtteranceRef.current = null
        window.__activeUtterance = null
        if (onEndCallback) onEndCallback()
      }

      window.speechSynthesis.speak(utterance)
    } catch (err) {
      console.warn('Browser speech error:', err)
      setIsPlayingAudio(false)
      if (onEndCallback) onEndCallback()
    }
  }

  // Unified speech synthesis player (Edge-TTS cloud with Web Speech API instant fallback)
  const handlePlaySpeech = (speechText) => {
    return new Promise(async (resolve) => {
      stopAllQuestionAudio()
      setIsPlayingAudio(true)

      let playedWithBackend = false
      try {
        const fetchPromise = synthesizeSpeech(speechText)
        const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('TTS_TIMEOUT')), 2500))

        const res = await Promise.race([fetchPromise, timeoutPromise])
        if (res && res.audio_base64 && res.audio_format === 'mp3') {
          const audioSrc = `data:audio/${res.audio_format};base64,${res.audio_base64}`
          const audio = new Audio(audioSrc)
          audioPlayerRef.current = audio
          audio.onended = () => {
            setIsPlayingAudio(false)
            audioPlayerRef.current = null
            resolve()
          }
          audio.onerror = () => {
            audioPlayerRef.current = null
            speakWithBrowserWebSpeech(speechText, resolve)
          }
          await audio.play()
          playedWithBackend = true
        }
      } catch (e) {
        console.log('ℹ️ Utilizing Browser Speech Synthesis:', e?.message || e)
      }

      if (!playedWithBackend) {
        speakWithBrowserWebSpeech(speechText, resolve)
      }
    })
  }

  // Read question aloud via TTS (Backend Edge-TTS / Web Speech API)
  const handlePlayQuestionAudio = async (textToPlay = null) => {
    // If currently playing, toggle to stop
    if (isPlayingAudio) {
      stopAllQuestionAudio()
      return
    }

    const qNum = activeQuestion?.question_number || 1
    const rawText = textToPlay || activeQuestion?.question_text || activeQuestion?.title || 'Walk me through the architecture of the most complex system you have built.'
    const speechText = textToPlay
      ? textToPlay
      : (activeQuestion?.is_followup
          ? `Follow-up question ${activeQuestion.followup_number}: ${rawText}`
          : `Question ${qNum}: ${rawText}`)

    await handlePlaySpeech(speechText)
  }

  // Speak evaluation result + transition to follow-up question (max 2 followups per question)
  const handleSpeakEvaluationAndFollowup = async (evalRes) => {
    const feedbackText = evalRes?.feedback || "Thank you for your answer."
    const followupQuestion = evalRes?.suggested_followup
    const currentFollowups = followupCount

    // Rule: Maximum 2 follow-up questions per main question
    const canAskFollowup = currentFollowups < 2 && Boolean(followupQuestion)

    let spokenMessage = ""
    if (canAskFollowup) {
      const nextFNum = currentFollowups + 1
      spokenMessage = `${feedbackText} Here is follow-up question ${nextFNum}: ${followupQuestion}`
    } else if (currentFollowups >= 2) {
      spokenMessage = `${feedbackText} We have thoroughly explored this question. You can now advance to the next question.`
    } else {
      spokenMessage = feedbackText
    }

    // AI Coach speaks evaluation feedback + follow-up
    await handlePlaySpeech(spokenMessage)

    // If follow-up allowed, update active question state to the follow-up
    if (canAskFollowup) {
      const nextFNum = currentFollowups + 1
      setFollowupCount(nextFNum)

      const originalQText = activeQuestion.original_question_text || activeQuestion.question_text || activeQuestion.title
      setActiveQuestion({
        ...activeQuestion,
        original_question_text: originalQText,
        is_followup: true,
        followup_number: nextFNum,
        question_text: followupQuestion,
        intent: `Follow-up ${nextFNum} of 2: Probing deeper into technical details, trade-offs, and metrics.`,
        expected_points: ["Concrete technical trade-offs", "Quantifiable metrics and edge case handling"]
      })

      // Reset recording state so candidate can record their response to this follow-up
      setRecordedAnswer(null)
      if (recordedAudioUrlRef.current) {
        URL.revokeObjectURL(recordedAudioUrlRef.current)
        recordedAudioUrlRef.current = null
      }
      setRecordedAudioUrl(null)
      setRecordingError(null)
    }
  }

  // Advance to next prompt
  const handleNextPrompt = async () => {
    stopAllQuestionAudio()
    setFollowupCount(0) // Reset follow-up counter for new main question!
    setEvaluation(null)
    setRecordedAnswer(null)
    if (recordedAudioUrlRef.current) {
      URL.revokeObjectURL(recordedAudioUrlRef.current)
      recordedAudioUrlRef.current = null
    }
    setRecordedAudioUrl(null)
    setRecordingError(null)
    setRecording(false)
    setSeconds(0)

    if (session && session.session_id) {
      try {
        const nextQ = await getNextQuestion(session.session_id)
        if (nextQ) {
          setActiveQuestion(nextQ)
          return
        }
      } catch (err) {
        console.warn('Next question fetch note:', err)
      }
    }

    const curIdx = fallbackQuestions.findIndex((q) => q.question_number === activeQuestion?.question_number)
    const nextIdx = (curIdx + 1) % fallbackQuestions.length
    setActiveQuestion(fallbackQuestions[nextIdx])
  }

  // Conclude interview session
  const finishPractice = async () => {
    stopAllQuestionAudio()
    if (recording) stopAudioRecording()
    const next = completed + 1
    setCompleted(next)
    localStorage.setItem('prep-completed', String(next))
    setSeconds(0)

    if (recordedAudioUrlRef.current) {
      URL.revokeObjectURL(recordedAudioUrlRef.current)
      recordedAudioUrlRef.current = null
    }
    setRecordedAudioUrl(null)
    setRecordedAnswer(null)
    setRecordingError(null)

    if (session && session.session_id) {
      try {
        await endInterview(session.session_id)
      } catch (e) {
        console.warn('End interview note:', e)
      }
    }

    setToastMessage('Session complete. Excellent work showing up!')
    setShowToast(true)
    window.setTimeout(() => setShowToast(false), 3500)
    setIsInInterviewRoom(false)
    setSession(null)
    setEvaluation(null)
  }

  const formatTime = (value) => `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`

  // ---------------------------------------------------------
  // 1. DEDICATED LIVE INTERVIEW ROOM PAGE
  // ---------------------------------------------------------
  if (isInInterviewRoom) {
    return (
      <>
        <InterviewRoomPage
          session={session}
          activeQuestion={activeQuestion}
          recording={recording}
          seconds={seconds}
          formatTime={formatTime}
          onStartRecording={startAudioRecording}
          onStopRecording={stopAudioRecording}
          onRetryRecording={handleRetryRecording}
          onNextQuestion={handleNextPrompt}
          onFinishSession={finishPractice}
          onExit={() => {
            stopAllQuestionAudio()
            setIsInInterviewRoom(false)
          }}
          evaluation={evaluation}
          recordedAnswer={recordedAnswer}
          recordedAudioUrl={recordedAudioUrl}
          recordingError={recordingError}
          isAnalyzing={isAnalyzing}
          onPlayAudio={handlePlayQuestionAudio}
          isPlayingAudio={isPlayingAudio}
          followupCount={followupCount}
        />
        {showToast && <div className="toast"><span>✓</span> {toastMessage}</div>}
      </>
    )
  }

  // ---------------------------------------------------------
  // 2. DASHBOARD / PREPARATION & SCHEDULING PAGE
  // ---------------------------------------------------------
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#interview" onClick={(event) => event.preventDefault()}>
          <span className="brand-mark">f</span><span>frame<span className="brand-dot">.</span></span>
        </a>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="main-nav" aria-label="Main navigation">
          {navItems.map((item) => (
            <button key={item.id} className="nav-item selected">
              <span className="nav-icon">{item.icon}</span>
              {item.label}
              <span className="nav-new">READY</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-card">
          <div className="sidebar-card-icon">✦</div>
          <strong>Schedule your interview.</strong>
          <p>Upload your JD & Resume to calibrate custom interview questions.</p>
          <button onClick={handleOpenScheduleModal}>
            Schedule Interview <span>↗</span>
          </button>
        </div>
        <button className="profile">
          <span className="avatar">S</span>
          <span className="profile-copy">
            <strong>Candidate</strong>
            <small>Setup Stage</small>
          </span>
          <span className="profile-menu">•••</span>
        </button>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> <strong>Interview Preparation</strong>
          </div>
          <div className="top-actions">
            <span className="streak"><span>✦</span> 3 day streak</span>
            <button className="icon-button" aria-label="Notifications">♧<i /></button>
            <div className="top-avatar">S</div>
          </div>
        </header>

        <div className="content">
          <section className="practice-page">
            <div className="eyebrow">
              INTERVIEW PREPARATION & SCHEDULING
              <span className="eyebrow-line" />
            </div>

            <div className="practice-heading">
              <div>
                <h1>Schedule your practice interview.</h1>
                <p>
                  Add your target Job Description and Resume to generate custom questions,
                  then enter your dedicated audio interview room.
                </p>
              </div>
            </div>

            <div className="practice-layout">
              <CameraPreviewCard
                recording={false}
                seconds={0}
                formatTime={formatTime}
                micEnabled={micEnabled}
                onToggleMic={() => setMicEnabled(!micEnabled)}
                cameraEnabled={cameraEnabled}
                onToggleCamera={() => setCameraEnabled(!cameraEnabled)}
              />

              <PromptCard
                isInInterviewRoom={false}
                activeQuestion={activeQuestion}
                recording={false}
                onScheduleInterview={handleOpenScheduleModal}
                onRecordOrStop={() => {}}
                onFinish={() => {}}
                evaluation={null}
                isAnalyzing={false}
                onPlayAudio={null}
                isPlayingAudio={false}
              />
            </div>
          </section>
        </div>
      </main>

      {/* Schedule Interview Modal: Step 1 (JD Input) -> Step 2 (Resume Input) */}
      <JobDescriptionModal
        isOpen={isScheduling}
        jobDescription={jobDescription}
        onChangeJobDescription={setJobDescription}
        jdFile={jdFile}
        setJdFile={setJdFile}
        resumeFile={resumeFile}
        setResumeFile={setResumeFile}
        resumeText={resumeText}
        setResumeText={setResumeText}
        onClose={() => setIsScheduling(false)}
        onStart={handleProcessAndEnterInterviewRoom}
        isProcessing={isSettingUp}
      />

      {showToast && <div className="toast"><span>✓</span> {toastMessage}</div>}
    </div>
  )
}

export default App
