const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Upload Job Description (File or Text)
 */
export async function uploadJobDescription({ file, text }) {
  const formData = new FormData();
  if (file) formData.append('file', file);
  if (text) formData.append('text', text);

  const res = await fetch(`${API_BASE}/api/v1/jd/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Failed to upload JD: ${res.statusText}`);
  return await res.json();
}

/**
 * Upload Resume (File or Text)
 */
export async function uploadResume({ file, text }) {
  const formData = new FormData();
  if (file) {
    formData.append('file', file);
  } else if (text) {
    const textBlob = new Blob([text], { type: 'text/plain' });
    formData.append('file', textBlob, 'resume.txt');
  }

  const res = await fetch(`${API_BASE}/api/v1/resume/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Failed to upload resume: ${res.statusText}`);
  return await res.json();
}

/**
 * Start Interview Session
 */
export async function startInterviewSession({ planOrRole = 'Fullstack Software Engineer', difficulty = 'intermediate' } = {}) {
  const res = await fetch(`${API_BASE}/api/v1/interview/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plan_or_role: planOrRole, difficulty }),
  });
  if (!res.ok) throw new Error(`Failed to start interview: ${res.statusText}`);
  return await res.json();
}

/**
 * Get current active question
 */
export async function getCurrentQuestion(sessionId) {
  const res = await fetch(`${API_BASE}/api/v1/interview/${sessionId}/question`);
  if (!res.ok) throw new Error(`Failed to get current question: ${res.statusText}`);
  return await res.json();
}

/**
 * Advance to next question
 */
export async function getNextQuestion(sessionId) {
  const res = await fetch(`${API_BASE}/api/v1/interview/${sessionId}/next`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to get next question: ${res.statusText}`);
  return await res.json();
}

/**
 * Submit candidate answer and receive STAR evaluation
 */
export async function submitAnswer(sessionId, { questionId, questionText, answerText, expectedPoints = [] }) {
  const res = await fetch(`${API_BASE}/api/v1/interview/${sessionId}/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question_id: questionId,
      question_text: questionText,
      answer_text: answerText,
      expected_points: expectedPoints,
    }),
  });
  if (!res.ok) throw new Error(`Failed to evaluate answer: ${res.statusText}`);
  return await res.json();
}

/**
 * End interview session
 */
export async function endInterview(sessionId) {
  const res = await fetch(`${API_BASE}/api/v1/interview/${sessionId}/end`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to end interview: ${res.statusText}`);
  return await res.json();
}

/**
 * Generate Entire Session Evaluation Report (saves to Sessions/{sessionId}.json)
 */
export async function generateSessionReport(sessionId, targetRole = null) {
  const res = await fetch(`${API_BASE}/api/v1/reports/generate/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_role: targetRole }),
  });
  if (!res.ok) throw new Error(`Failed to generate session report: ${res.statusText}`);
  return await res.json();
}

/**
 * Get Saved Session Report from Sessions/{sessionId}.json
 */
export async function getSessionReport(sessionId) {
  const res = await fetch(`${API_BASE}/api/v1/reports/${sessionId}`);
  if (!res.ok) throw new Error(`Failed to get session report: ${res.statusText}`);
  return await res.json();
}

/**
 * Transcribe candidate voice audio via Groq Whisper backend
 */
export async function transcribeAudio(audioBlob) {
  const formData = new FormData();
  let ext = 'webm';
  if (audioBlob.type?.includes('mp4') || audioBlob.type?.includes('m4a')) {
    ext = 'mp4';
  } else if (audioBlob.type?.includes('ogg')) {
    ext = 'ogg';
  } else if (audioBlob.type?.includes('wav')) {
    ext = 'wav';
  }

  formData.append('file', audioBlob, `candidate_voice.${ext}`);
  formData.append('language', 'en');

  const res = await fetch(`${API_BASE}/api/v1/voice/transcribe`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    const message = errData.detail || `Server transcription failed (${res.status}: ${res.statusText})`;
    throw new Error(message);
  }

  return await res.json();
}

/**
 * Synthesize interviewer speech
 */
export async function synthesizeSpeech(text, voice = 'en-US-JennyNeural') {
  const res = await fetch(`${API_BASE}/api/v1/voice/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice }),
  });
  if (!res.ok) throw new Error(`Speech synthesis failed: ${res.statusText}`);
  return await res.json();
}

/**
 * Detect filler words in answer transcript
 */
export async function detectFillers(text) {
  const res = await fetch(`${API_BASE}/api/v1/voice/detect-fillers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`Filler detection failed: ${res.statusText}`);
  return await res.json();
}
