import React, { useEffect, useRef, useState } from 'react';
import { Orb } from '@yogesharc/thinking-orbs';
import Button from './Button';

const DIFFICULTY_OPTIONS = [
  {
    key: 'beginner',
    label: 'Beginner',
    tag: 'Core Fundamentals',
    tagColor: '#34d399',
    tagBg: '#05966926',
    icon: '🌱',
    questions: 'Fundamentals & what you built. Simple, single-concept questions with no ambiguity. Small single-service scenarios.',
    evaluation: 'Rewards correct basics and clear reasoning. Zero penalty for missing high-scale trade-offs or production metrics.',
  },
  {
    key: 'intermediate',
    label: 'Intermediate',
    badge: 'Recommended',
    tag: 'Practical & Trade-offs',
    tagColor: '#60a5fa',
    tagBg: '#2563eb26',
    icon: '⚡',
    questions: 'Practical implementation choices, debugging and common trade-offs. Moderate scale systems with 1-2 components.',
    evaluation: 'Expects correct reasoning, trade-offs, and concrete examples. Minor edge case gaps are acceptable.',
  },
  {
    key: 'advanced',
    label: 'Advanced',
    tag: 'Constraints & Failures',
    tagColor: '#c084fc',
    tagBg: '#7c3aed26',
    icon: '🔥',
    questions: 'Design under constraints, latency, failure modes, real ambiguity, and ownership. Justify technical decisions.',
    evaluation: 'Expects rigorous trade-offs, edge cases, measurable metrics, and clear ownership. Vague answers score low.',
  },
  {
    key: 'expert',
    label: 'Expert',
    tag: 'Architecture & Strategy',
    tagColor: '#f472b6',
    tagBg: '#db277726',
    icon: '👑',
    questions: 'Architecture at scale, consistency, cost, org-level trade-offs, mentoring, and technical strategy.',
    evaluation: 'Expects deep reasoning, alternatives considered, risk mitigation, and leadership impact. Surface-level answers score low.',
  },
];

export function JobDescriptionModal({
  isOpen,
  jobDescription,
  onChangeJobDescription,
  jdFile,
  setJdFile,
  resumeFile,
  setResumeFile,
  resumeText,
  setResumeText,
  difficulty = 'intermediate',
  setDifficulty,
  onClose,
  onStart,
  isProcessing = false,
}) {
  const [step, setStep] = useState('jd'); // 'jd' | 'resume' | 'difficulty'
  const [jdTab, setJdTab] = useState('paste'); // 'upload' | 'paste'
  const [resumeTab, setResumeTab] = useState('upload'); // 'upload' | 'paste'
  const [isJdDragging, setIsJdDragging] = useState(false);
  const [isResumeDragging, setIsResumeDragging] = useState(false);

  const jdFileInputRef = useRef(null);
  const resumeFileInputRef = useRef(null);

  // Reset to Step 1 (JD) whenever modal opens
  useEffect(() => {
    if (isOpen) {
      setStep('jd');
    }
  }, [isOpen]);

  // Handle Escape key: difficulty -> resume -> jd -> close modal
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (step === 'difficulty') {
          e.stopPropagation();
          setStep('resume');
        } else if (step === 'resume') {
          e.stopPropagation();
          setStep('jd');
        } else {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, step, onClose]);

  if (!isOpen) return null;

  const handleJdFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file && setJdFile) {
      setJdFile(file);
    }
  };

  const handleResumeFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file && setResumeFile) {
      setResumeFile(file);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 KB';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  const currentDiffOption = DIFFICULTY_OPTIONS.find((d) => d.key === difficulty) || DIFFICULTY_OPTIONS[1];

  return (
    <div className="jd-modal-backdrop" onClick={onClose}>
      <div
        className="camera-panel jd-modal-shell"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Interview Setup"
      >
        {/* Top bar with Step Indicator */}
        <div className="camera-top">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {step === 'resume' && (
              <button
                type="button"
                className="text-link"
                onClick={() => setStep('jd')}
                style={{ fontSize: '9px', fontWeight: 'bold', marginRight: '4px' }}
                title="Back to Job Description"
              >
                ← Back
              </button>
            )}
            {step === 'difficulty' && (
              <button
                type="button"
                className="text-link"
                onClick={() => setStep('resume')}
                style={{ fontSize: '9px', fontWeight: 'bold', marginRight: '4px' }}
                title="Back to Resume"
              >
                ← Back
              </button>
            )}
            <span>
              <i style={{ background: '#9d86ec', boxShadow: '0 0 0 3px #ede8fa' }} />
              {step === 'jd'
                ? 'JOB DESCRIPTION'
                : step === 'resume'
                ? 'RESUME UPLOAD'
                : 'INTERVIEW COMPLEXITY'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span className="camera-status">
              {step === 'jd'
                ? '● Step 1 of 3'
                : step === 'resume'
                ? '● Step 2 of 3'
                : '● Step 3 of 3'}
            </span>
            <button
              type="button"
              className="text-link"
              onClick={onClose}
              style={{ fontSize: '11px', cursor: 'pointer', color: '#9b94a6' }}
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Sliding Viewport & Track */}
        <div className="setup-stage-viewport">
          <div
            className="setup-steps-track"
            style={{
              transform:
                step === 'jd'
                  ? 'translateX(0%)'
                  : step === 'resume'
                  ? 'translateX(-33.333333%)'
                  : 'translateX(-66.666666%)',
            }}
          >
            {/* Slide 1: Job Description Card */}
            <div className="setup-step-slide">
              <div className="jd-container jd-overlay-container">
                <div className="jd-header jd-overlay-header">
                  <div>
                    <strong>Target Job Description & Role Requirements</strong>
                    <span>Upload or paste the role description and responsibilities.</span>
                  </div>
                  <div className="resume-mode-tabs">
                    <button
                      type="button"
                      className={`resume-tab ${jdTab === 'upload' ? 'active' : ''}`}
                      onClick={() => setJdTab('upload')}
                    >
                      📁 Upload File
                    </button>
                    <button
                      type="button"
                      className={`resume-tab ${jdTab === 'paste' ? 'active' : ''}`}
                      onClick={() => setJdTab('paste')}
                    >
                      📝 Paste Text
                    </button>
                  </div>
                </div>

                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                  {jdTab === 'upload' ? (
                    jdFile ? (
                      <div className="resume-selected-card">
                        <div className="resume-file-info">
                          <div className="resume-file-icon">📄</div>
                          <div className="resume-file-details">
                            <strong>{jdFile.name}</strong>
                            <span>{formatFileSize(jdFile.size)} • Ready for analysis</span>
                          </div>
                          <button
                            type="button"
                            className="resume-remove-btn"
                            onClick={() => setJdFile && setJdFile(null)}
                            title="Remove file"
                          >
                            ✕
                          </button>
                        </div>
                        <button
                          type="button"
                          className="resume-dropzone-btn"
                          onClick={() => jdFileInputRef.current?.click()}
                        >
                          Replace with another file
                        </button>
                        <input
                          ref={jdFileInputRef}
                          type="file"
                          accept=".pdf,.doc,.docx,.txt"
                          style={{ display: 'none' }}
                          onChange={handleJdFileChange}
                        />
                      </div>
                    ) : (
                      <div
                        className={`resume-dropzone ${isJdDragging ? 'dragging' : ''}`}
                        onDragOver={(e) => {
                          e.preventDefault();
                          setIsJdDragging(true);
                        }}
                        onDragLeave={() => setIsJdDragging(false)}
                        onDrop={(e) => {
                          e.preventDefault();
                          setIsJdDragging(false);
                          const file = e.dataTransfer.files?.[0];
                          if (file && setJdFile) setJdFile(file);
                        }}
                        onClick={() => jdFileInputRef.current?.click()}
                      >
                        <input
                          ref={jdFileInputRef}
                          type="file"
                          accept=".pdf,.doc,.docx,.txt"
                          style={{ display: 'none' }}
                          onChange={handleJdFileChange}
                        />
                        <div className="resume-dropzone-icon">⇪</div>
                        <strong>Click to upload or drag & drop job description</strong>
                        <span>Supports PDF, DOCX, DOC, or TXT up to 10MB</span>
                        <div className="resume-dropzone-btn">Browse File from Device</div>
                      </div>
                    )
                  ) : (
                    <textarea
                      className="jd-textarea jd-overlay-textarea"
                      value={jobDescription}
                      onChange={(e) => onChangeJobDescription(e.target.value)}
                      placeholder="Paste target job description, responsibilities, or required skills here...&#10;&#10;e.g. Senior Frontend Engineer with 4+ years experience in React, TypeScript, state management, web performance, and STAR methodology..."
                      spellCheck={false}
                      autoComplete="off"
                      autoCorrect="off"
                      autoCapitalize="off"
                      data-gramm="false"
                      data-gramm_editor="false"
                      data-enable-grammarly="false"
                    />
                  )}
                </div>

                <div className="jd-modal-footer">
                  <button
                    type="button"
                    className="modal-footer-back-btn"
                    aria-label="Close"
                    title="Close"
                    onClick={onClose}
                  >
                    ✕
                  </button>
                  <span>Private and stored only in your browser.</span>
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
                    <Button onClick={() => setStep('resume')} text="Next: Add Resume ↗" />
                  </div>
                </div>
              </div>
            </div>

            {/* Slide 2: Resume Input Card */}
            <div className="setup-step-slide">
              <div className="jd-container jd-overlay-container">
                <div className="jd-header jd-overlay-header">
                  <div>
                    <strong>Candidate Resume & Experience</strong>
                    <span>Add your resume so questions align with your past work.</span>
                  </div>
                  <div className="resume-mode-tabs">
                    <button
                      type="button"
                      className={`resume-tab ${resumeTab === 'upload' ? 'active' : ''}`}
                      onClick={() => setResumeTab('upload')}
                    >
                      📁 Upload File
                    </button>
                    <button
                      type="button"
                      className={`resume-tab ${resumeTab === 'paste' ? 'active' : ''}`}
                      onClick={() => setResumeTab('paste')}
                    >
                      📝 Paste Text
                    </button>
                  </div>
                </div>

                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                  {resumeTab === 'upload' ? (
                    resumeFile ? (
                      <div className="resume-selected-card">
                        <div className="resume-file-info">
                          <div className="resume-file-icon">📄</div>
                          <div className="resume-file-details">
                            <strong>{resumeFile.name}</strong>
                            <span>{formatFileSize(resumeFile.size)} • Ready for analysis</span>
                          </div>
                          <button
                            type="button"
                            className="resume-remove-btn"
                            onClick={() => setResumeFile && setResumeFile(null)}
                            title="Remove file"
                          >
                            ✕
                          </button>
                        </div>
                        <button
                          type="button"
                          className="resume-dropzone-btn"
                          onClick={() => resumeFileInputRef.current?.click()}
                        >
                          Replace with another file
                        </button>
                        <input
                          ref={resumeFileInputRef}
                          type="file"
                          accept=".pdf,.doc,.docx,.txt"
                          style={{ display: 'none' }}
                          onChange={handleResumeFileChange}
                        />
                      </div>
                    ) : (
                      <div
                        className={`resume-dropzone ${isResumeDragging ? 'dragging' : ''}`}
                        onDragOver={(e) => {
                          e.preventDefault();
                          setIsResumeDragging(true);
                        }}
                        onDragLeave={() => setIsResumeDragging(false)}
                        onDrop={(e) => {
                          e.preventDefault();
                          setIsResumeDragging(false);
                          const file = e.dataTransfer.files?.[0];
                          if (file && setResumeFile) setResumeFile(file);
                        }}
                        onClick={() => resumeFileInputRef.current?.click()}
                      >
                        <input
                          ref={resumeFileInputRef}
                          type="file"
                          accept=".pdf,.doc,.docx,.txt"
                          style={{ display: 'none' }}
                          onChange={handleResumeFileChange}
                        />
                        <div className="resume-dropzone-icon">⇪</div>
                        <strong>Click to upload or drag & drop resume</strong>
                        <span>Supports PDF, DOCX, DOC, or TXT up to 10MB</span>
                        <div className="resume-dropzone-btn">Browse File from Device</div>
                      </div>
                    )
                  ) : (
                    <textarea
                      className="jd-textarea jd-overlay-textarea"
                      value={resumeText}
                      onChange={(e) => setResumeText(e.target.value)}
                      placeholder="Paste your resume content, experience, projects, or background here...&#10;&#10;e.g. Senior Frontend Engineer with 4+ years building high performance React applications..."
                      spellCheck={false}
                      autoComplete="off"
                      autoCorrect="off"
                      autoCapitalize="off"
                      data-gramm="false"
                      data-gramm_editor="false"
                      data-enable-grammarly="false"
                    />
                  )}
                </div>

                <div className="jd-modal-footer">
                  <button
                    type="button"
                    className="modal-footer-back-btn"
                    aria-label="Back to Job Description"
                    title="Back to Job Description"
                    onClick={() => setStep('jd')}
                  >
                    ←
                  </button>
                  <span>Parsed locally for question matching.</span>
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
                    <Button onClick={() => setStep('difficulty')} text="Next: Choose Complexity ↗" />
                  </div>
                </div>
              </div>
            </div>

            {/* Slide 3: Interview Complexity Card */}
            <div className="setup-step-slide">
              <div className="jd-container jd-overlay-container">
                <div className="jd-header jd-overlay-header">
                  <div>
                    <strong>Interview Difficulty & Calibration</strong>
                    <span>Select candidate seniority level to calibrate question depth and evaluation.</span>
                  </div>
                  <div className="difficulty-current-pill">
                    Level: <strong>{currentDiffOption.label}</strong>
                  </div>
                </div>

                <div className="difficulty-selector-container">
                  <div className="difficulty-grid">
                    {DIFFICULTY_OPTIONS.map((item) => {
                      const isSelected = (difficulty || 'intermediate') === item.key;
                      return (
                        <div
                          key={item.key}
                          className={`difficulty-card ${isSelected ? 'active' : ''}`}
                          onClick={() => setDifficulty && setDifficulty(item.key)}
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              setDifficulty && setDifficulty(item.key);
                            }
                          }}
                        >
                          <div className="difficulty-card-top">
                            <div className="difficulty-card-title-group">
                              <span className="difficulty-icon">{item.icon}</span>
                              <strong className="difficulty-label">{item.label}</strong>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              {item.badge && <span className="difficulty-badge-rec">{item.badge}</span>}
                              <span
                                className="difficulty-tag"
                                style={{ color: item.tagColor, backgroundColor: item.tagBg }}
                              >
                                {item.tag}
                              </span>
                            </div>
                          </div>

                          <div className="difficulty-card-body">
                            <div className="difficulty-rule-row">
                              <span className="rule-label">Questions:</span>
                              <p className="rule-text">{item.questions}</p>
                            </div>
                            <div className="difficulty-rule-row">
                              <span className="rule-label">Evaluation:</span>
                              <p className="rule-text">{item.evaluation}</p>
                            </div>
                          </div>

                          {isSelected && (
                            <div className="difficulty-selected-indicator">
                              <span>✓ Selected</span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="jd-modal-footer">
                  <button
                    type="button"
                    className="modal-footer-back-btn"
                    aria-label="Back to Resume"
                    title="Back to Resume"
                    onClick={() => setStep('resume')}
                  >
                    ←
                  </button>
                  <span>Calibrated with LLM evaluation prompt & question guidelines.</span>
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
                    <Button
                      onClick={isProcessing ? undefined : onStart}
                      disabled={isProcessing}
                      showSparkle={!isProcessing}
                    >
                      {isProcessing ? (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                          <Orb state="searching" variant="lighthouse" size={15} />
                          Matching & Calibrating...
                        </span>
                      ) : (
                        'Start Interview ↗'
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default JobDescriptionModal;

