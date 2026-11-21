import React, { useRef, useState } from 'react';
import Button from './Button';

export function ResumeUploadModal({
  isOpen,
  resumeFile,
  setResumeFile,
  resumeText,
  setResumeText,
  onClose,
  onStart,
}) {
  const [activeTab, setActiveTab] = useState('upload');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setResumeFile(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setResumeFile(file);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 KB';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="jd-modal-backdrop" onClick={onClose}>
      <div className="camera-panel jd-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="camera-top">
          <span>
            <i style={{ background: '#9d86ec', boxShadow: '0 0 0 3px #ede8fa' }} />
            RESUME UPLOAD
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span className="camera-status">● Step 2 of 2</span>
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

        <div className="camera-stage jd-overlay-stage">
          <div className="jd-container jd-overlay-container">
            <div className="jd-header jd-overlay-header">
              <div>
                <strong>Upload Resume or Experience Details</strong>
                <span>Add your resume so your mock interview questions match your background.</span>
              </div>
              <div className="resume-mode-tabs">
                <button
                  type="button"
                  className={`resume-tab ${activeTab === 'upload' ? 'active' : ''}`}
                  onClick={() => setActiveTab('upload')}
                >
                  📁 Upload File
                </button>
                <button
                  type="button"
                  className={`resume-tab ${activeTab === 'paste' ? 'active' : ''}`}
                  onClick={() => setActiveTab('paste')}
                >
                  📝 Paste Text
                </button>
              </div>
            </div>

            {activeTab === 'upload' ? (
              resumeFile ? (
                <div className="resume-selected-card">
                  <div className="resume-file-info">
                    <div className="resume-file-icon">📄</div>
                    <div className="resume-file-details">
                      <strong>{resumeFile.name}</strong>
                      <span>{formatFileSize(resumeFile.size)} • Ready for interview analysis</span>
                    </div>
                    <button
                      type="button"
                      className="resume-remove-btn"
                      onClick={() => setResumeFile(null)}
                      title="Remove file"
                    >
                      ✕
                    </button>
                  </div>
                  <button
                    type="button"
                    className="resume-dropzone-btn"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Replace with another file
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.doc,.docx,.txt"
                    style={{ display: 'none' }}
                    onChange={handleFileChange}
                  />
                </div>
              ) : (
                <div
                  className={`resume-dropzone ${isDragging ? 'dragging' : ''}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.doc,.docx,.txt"
                    style={{ display: 'none' }}
                    onChange={handleFileChange}
                  />
                  <div className="resume-dropzone-icon">⇪</div>
                  <strong>Click to upload or drag & drop your resume</strong>
                  <span>Supports PDF, DOCX, DOC, or TXT up to 10MB</span>
                  <div className="resume-dropzone-btn">Choose File from Device</div>
                </div>
              )
            ) : (
              <textarea
                className="jd-textarea jd-overlay-textarea"
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                placeholder="Paste your resume content, key projects, education, and technical experience here...&#10;&#10;e.g. Full-stack Developer with 3+ years experience building scalable web applications with React, Node.js, and PostgreSQL..."
                spellCheck={false}
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                data-gramm="false"
                data-gramm_editor="false"
                data-enable-grammarly="false"
              />
            )}

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
              <span>Resume is analyzed privately and kept in your browser.</span>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
                <Button onClick={onStart}>
                  Start Interview ↗
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ResumeUploadModal;
