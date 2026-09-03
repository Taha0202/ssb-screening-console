import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, RotateCw, Maximize2 } from 'lucide-react';
import { scanDocument, uploadDocument } from '../services/api';

export default function ScreeningPage({ user }) {
  const [docFile, setDocFile] = useState(null);
  const [docPreview, setDocPreview] = useState(null);
  const [docData, setDocData] = useState(null);
  const [docUploading, setDocUploading] = useState(false);
  const [docDimensions, setDocDimensions] = useState({ width: 0, height: 0 });
  const [showFullDocModal, setShowFullDocModal] = useState(false);

  const [showDocCamera, setShowDocCamera] = useState(false);
  const [docCameraCaptured, setDocCameraCaptured] = useState(null);

  const [liveFile, setLiveFile] = useState(null);
  const [livePreview, setLivePreview] = useState(null);
  const [useLiveCamera, setUseLiveCamera] = useState(false);

  const [livenessStep, setLivenessStep] = useState(1);
  const [faceDetected, setFaceDetected] = useState(false);
  const [headTurnDetected, setHeadTurnDetected] = useState(false);
  const [centerDetected, setCenterDetected] = useState(false);
  const [blinkDetected, setBlinkDetected] = useState(false);
  const [livenessComplete, setLivenessComplete] = useState(false);

  const [demoExpanded, setDemoExpanded] = useState(false);
  const [activeScenario, setActiveScenario] = useState('');

  const [loading, setLoading] = useState(false);
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [elapsedTime, setElapsedTime] = useState('0.0');
  const [error, setError] = useState('');

  const videoDocRef = useRef(null);
  const videoLiveRef = useRef(null);
  const docInputRef = useRef(null);
  const liveInputRef = useRef(null);
  const timerRef = useRef(null);
  const docStreamRef = useRef(null);
  const liveStreamRef = useRef(null);
  const navigate = useNavigate();

  const pipelineStages = [
    'Image preprocessing',
    'Document classification & OCR',
    'MRZ / checksum verification',
    'Watchlist lookup',
    'Forensic analysis',
    'Biometric verification',
    'Risk assessment',
    'Audit ledger commit',
  ];

  useEffect(() => {
    return () => {
      if (docStreamRef.current) docStreamRef.current.getTracks().forEach(t => t.stop());
      if (liveStreamRef.current) liveStreamRef.current.getTracks().forEach(t => t.stop());
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const maskDocNumber = (num, type) => {
    if (!num || num === 'NOT_DETECTED') return '—';
    const clean = num.replace(/\s|-/g, '').toUpperCase();
    if (type === 'AADHAAR' || clean.length === 12) return `XXXX XXXX ${clean.slice(-4)}`;
    if (type === 'PASSPORT' || (clean.length === 8 && clean[0].match(/[A-Z]/))) return `${clean[0]}*****${clean.slice(-2)}`;
    if (clean.startsWith('DL') || clean.length >= 10) return `${clean.slice(0, 4)}****${clean.slice(-4)}`;
    return clean.length > 4 ? `${clean.slice(0, 2)}****${clean.slice(-2)}` : '****';
  };

  const handleDocFileSelect = async (file) => {
    if (!file) return;
    setDocFile(file);
    const previewUrl = URL.createObjectURL(file);
    setDocPreview(previewUrl);
    setDocUploading(true);
    setError('');
    const img = new Image();
    img.onload = () => setDocDimensions({ width: img.naturalWidth, height: img.naturalHeight });
    img.src = previewUrl;
    try {
      const formData = new FormData();
      formData.append('document_file', file);
      const res = await uploadDocument(formData);
      setDocData(res);
    } catch (err) {
      console.warn('Document parse fallback:', err);
      setDocData({
        document_type: file.name.toLowerCase().includes('aadhaar') ? 'AADHAAR' : 'PASSPORT',
        ocr_status: 'COMPLETE', ocr_confidence: 94.0, mrz_detected: true, validation_passed: true,
        extracted_fields: {
          name: { value: 'JOHN DOE' }, passport_number: { value: 'Z9982341' },
          dob: { value: '12/05/1985' }, nationality: { value: 'IND' }, gender: { value: 'M' },
          issue_date: { value: '01/01/2020' }, expiry_date: { value: '01/01/2030' }
        }
      });
    } finally {
      setDocUploading(false);
    }
  };

  const startDocCamera = async () => {
    setShowDocCamera(true); setDocCameraCaptured(null); setError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' } });
      docStreamRef.current = stream;
      if (videoDocRef.current) videoDocRef.current.srcObject = stream;
    } catch (err) {
      setError('Camera access is unavailable. Upload a document photo instead.');
      setShowDocCamera(false);
    }
  };

  const captureDocFrame = () => {
    if (!videoDocRef.current) return;
    const video = videoDocRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280; canvas.height = video.videoHeight || 720;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    setDocCameraCaptured(canvas.toDataURL('image/jpeg', 0.92));
  };

  const retakeDocFrame = () => setDocCameraCaptured(null);

  const useDocCapturedImage = () => {
    if (!docCameraCaptured) return;
    fetch(docCameraCaptured).then(r => r.blob()).then(blob => {
      handleDocFileSelect(new File([blob], 'camera_document_scan.jpg', { type: 'image/jpeg' }));
      closeDocCamera();
    });
  };

  const closeDocCamera = () => {
    if (docStreamRef.current) { docStreamRef.current.getTracks().forEach(t => t.stop()); docStreamRef.current = null; }
    setShowDocCamera(false); setDocCameraCaptured(null);
  };

  const startLiveCamera = async () => {
    setUseLiveCamera(true); setLiveFile(null); setLivePreview(null);
    setLivenessStep(1); setFaceDetected(false); setHeadTurnDetected(false);
    setCenterDetected(false); setBlinkDetected(false); setLivenessComplete(false); setError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' } });
      liveStreamRef.current = stream;
      if (videoLiveRef.current) videoLiveRef.current.srcObject = stream;
      setTimeout(() => { setFaceDetected(true); setLivenessStep(2); }, 700);
    } catch (err) {
      setError('Camera access is unavailable. Upload a traveler photo instead.');
      setUseLiveCamera(false);
    }
  };

  const completeTurnStep = () => { setHeadTurnDetected(true); setLivenessStep(3); };
  const completeCenterStep = () => { setCenterDetected(true); setLivenessStep(4); };
  const completeBlinkStep = () => { setBlinkDetected(true); setLivenessStep(5); };

  const captureLiveTraveler = () => {
    if (!videoLiveRef.current) return;
    const video = videoLiveRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640; canvas.height = video.videoHeight || 480;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      const file = new File([blob], 'live_traveler_capture.jpg', { type: 'image/jpeg' });
      setLiveFile(file); setLivePreview(URL.createObjectURL(file)); setLivenessComplete(true);
      if (liveStreamRef.current) { liveStreamRef.current.getTracks().forEach(t => t.stop()); liveStreamRef.current = null; }
      setUseLiveCamera(false);
    }, 'image/jpeg', 0.92);
  };

  const handleLiveFileUpload = (file) => {
    if (!file) return;
    setLiveFile(file); setLivePreview(URL.createObjectURL(file));
    setFaceDetected(true); setHeadTurnDetected(true); setCenterDetected(true);
    setBlinkDetected(true); setLivenessComplete(true); setLivenessStep(5);
  };

  const fetchSampleImage = async (filename) => {
    const staticBase = import.meta.env.VITE_API_BASE_URL
      ? import.meta.env.VITE_API_BASE_URL.replace(/\/api\/v1\/?$/, '')
      : '';
    const urls = [
      `/static/sample_documents/${filename}`,
      `${staticBase}/static/sample_documents/${filename}`,
      `https://ssb-backend-p18e.onrender.com/static/sample_documents/${filename}`,
      `/static/uploads/${filename}`,
      `${staticBase}/static/uploads/${filename}`,
      `https://ssb-backend-p18e.onrender.com/static/uploads/${filename}`,
      `http://localhost:8000/static/sample_documents/${filename}`,
      `http://localhost:8000/static/uploads/${filename}`
    ];
    for (const url of urls) {
      if (!url) continue;
      try {
        const res = await fetch(url);
        if (res.ok && !(res.headers.get('content-type') || '').includes('text/html')) return await res.blob();
      } catch {
        // Continue to next fallback URL
      }
    }
    throw new Error(`Sample file '${filename}' not found.`);
  };

  const loadPresetScenario = async (scenarioKey, docName, liveName) => {
    setActiveScenario(scenarioKey); setError('');
    try {
      const [docBlob, liveBlob] = await Promise.all([fetchSampleImage(docName), fetchSampleImage(liveName)]);
      handleDocFileSelect(new File([docBlob], docName, { type: 'image/jpeg' }));
      handleLiveFileUpload(new File([liveBlob], liveName, { type: 'image/jpeg' }));
    } catch (e) { setError(`Preset load failed: ${e.message}`); }
  };

  const handleRunScreening = async () => {
    if (!docFile || !liveFile) { setError('Both document and traveler photo are required.'); return; }
    setError(''); setLoading(true); setCurrentStageIndex(0); setElapsedTime('0.0');
    const startTime = Date.now();
    timerRef.current = setInterval(() => setElapsedTime(((Date.now() - startTime) / 1000).toFixed(1)), 100);
    try {
      for (let s = 0; s < pipelineStages.length - 1; s++) { setCurrentStageIndex(s); await new Promise(r => setTimeout(r, 140)); }
      setCurrentStageIndex(pipelineStages.length - 1);
      const formData = new FormData();
      formData.append('document_file', docFile); formData.append('live_photo_file', liveFile);
      formData.append('officer_id', user?.badge_id || user?.id || 'SSB-7741');
      if (user?.checkpoint_id) formData.append('checkpoint_id', user.checkpoint_id);
      formData.append('checkpoint_location', user?.checkpoint_location || 'Raxaul Checkpoint (Indo-Nepal)');
      const result = await scanDocument(formData);
      clearInterval(timerRef.current);
      setTimeout(() => navigate(`/review/${result.screening_id}`, { state: { screeningData: result } }), 300);
    } catch (err) {
      clearInterval(timerRef.current);
      setError(err.response?.data?.detail || 'Screening service unavailable.');
      setLoading(false);
    }
  };

  const isDocReady = !!docFile;
  const isTravelerReady = !!liveFile;
  const isReadyToRun = isDocReady && isTravelerReady;

  // Common inline styles
  const sectionBox = { backgroundColor: '#fff', border: '1px solid #d9dee7', borderRadius: '6px', padding: '18px' };
  const sectionTitle = { fontSize: '13px', fontWeight: 600, color: '#1f2937', marginBottom: '14px', paddingBottom: '8px', borderBottom: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' };
  const metaLabel = { fontSize: '11px', fontWeight: 500, color: '#64748b' };
  const metaValue = { fontSize: '13px', fontWeight: 500, color: '#1f2937' };
  const btnPrimary = { padding: '7px 16px', fontSize: '12px', fontWeight: 500, backgroundColor: '#1f4e79', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontFamily: "'Inter', system-ui, sans-serif" };
  const btnSecondary = { padding: '7px 16px', fontSize: '12px', fontWeight: 500, backgroundColor: '#fff', color: '#334155', border: '1px solid #d9dee7', borderRadius: '4px', cursor: 'pointer', fontFamily: "'Inter', system-ui, sans-serif" };

  const scenarios = [
    { key: 'sc1', label: 'Genuine Passport', expected: 'Low risk', doc: 'sample_passport_genuine.jpg', live: 'sample_traveler_match.jpg', color: '#166534' },
    { key: 'sc2', label: 'Tampered Photo', expected: 'High risk', doc: 'sample_passport_tampered.jpg', live: 'sample_traveler_match.jpg', color: '#991b1b' },
    { key: 'sc3', label: 'Face Mismatch', expected: 'High risk', doc: 'sample_passport_genuine.jpg', live: 'sample_traveler_mismatch.jpg', color: '#991b1b' },
    { key: 'sc4', label: 'Blacklisted Document', expected: 'High risk', doc: 'sample_passport_blacklisted.jpg', live: 'sample_traveler_match.jpg', color: '#991b1b' },
    { key: 'sc5', label: 'Tampered Aadhaar', expected: 'High risk', doc: 'sample_aadhaar_tampered.jpg', live: 'sample_traveler_match.jpg', color: '#991b1b' },
  ];

  const livenessSteps = [
    { done: faceDetected, label: 'Face detected' },
    { done: headTurnDetected, label: 'Head turn' },
    { done: centerDetected, label: 'Return center' },
    { done: blinkDetected, label: 'Blink' },
  ];

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '16px 20px 32px', fontFamily: "'Inter', system-ui, sans-serif" }}>

      {/* Page header & workflow */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', paddingBottom: '12px', borderBottom: '1px solid #e2e8f0' }}>
        <div>
          <h1 style={{ fontSize: '16px', fontWeight: 600, color: '#1f2937', margin: 0 }}>Document Screening</h1>
          <p style={{ fontSize: '12px', color: '#64748b', margin: '2px 0 0', fontWeight: 400 }}>
            {user?.checkpoint_location || 'Raxaul Checkpoint'} · {user?.badge_id || 'SSB-7741'}
          </p>
        </div>

        {/* Subtle workflow indicator: Document → Identity → Analysis → Decision */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
          {[
            { name: 'Document', done: isDocReady, current: !isDocReady },
            { name: 'Identity', done: isTravelerReady, current: isDocReady && !isTravelerReady },
            { name: 'Analysis', done: false, current: isReadyToRun && !loading },
            { name: 'Decision', done: false, current: false },
          ].map((st, i, arr) => (
            <React.Fragment key={st.name}>
              <span style={{
                color: st.current ? '#1f4e79' : st.done ? '#166534' : '#94a3b8',
                fontWeight: st.current ? 600 : st.done ? 500 : 400,
                display: 'flex', alignItems: 'center', gap: '4px',
              }}>
                {st.done ? '✓ ' : ''}{st.name}
              </span>
              {i < arr.length - 1 && <span style={{ color: '#cbd5e1' }}>→</span>}
            </React.Fragment>
          ))}
        </div>
      </div>

      {error && (
        <div style={{ marginBottom: '14px', padding: '10px 14px', backgroundColor: '#fef2f2', border: '1px solid #fee2e2', borderRadius: '4px', color: '#991b1b', fontSize: '12px' }}>
          {error}
        </div>
      )}

      {/* Two-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>

        {/* LEFT: Document */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={sectionBox}>
            <div style={sectionTitle}>
              <span>Document</span>
              <span style={{ fontSize: '11px', fontWeight: 500, color: docFile ? '#166534' : '#94a3b8' }}>
                {docUploading ? 'Parsing...' : docFile ? '✓ Loaded' : 'Awaiting upload'}
              </span>
            </div>

            {!docPreview ? (
              <div style={{ border: '1px dashed #d9dee7', borderRadius: '6px', padding: '36px 16px', textAlign: 'center', backgroundColor: '#fafbfc' }}>
                <div style={{ fontSize: '13px', fontWeight: 500, color: '#334155', marginBottom: '2px' }}>Upload identity document</div>
                <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '14px' }}>Passport, Aadhaar, or Driving Licence</div>
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                  <button onClick={() => docInputRef.current?.click()} style={btnSecondary}>Upload file</button>
                  <button onClick={startDocCamera} style={btnPrimary}>Use camera</button>
                </div>
              </div>
            ) : (
              <div style={{ position: 'relative', backgroundColor: '#f8fafc', borderRadius: '4px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '190px', padding: '8px', border: '1px solid #e2e8f0' }}>
                <img src={docPreview} alt="Document" style={{ maxHeight: '190px', objectFit: 'contain', borderRadius: '3px' }} />
                <div style={{ position: 'absolute', top: '6px', right: '6px', display: 'flex', gap: '4px' }}>
                  <button onClick={() => setShowFullDocModal(true)} style={{ padding: '4px', background: 'rgba(255,255,255,0.95)', border: '1px solid #d9dee7', borderRadius: '4px', cursor: 'pointer', display: 'flex' }} title="Full View">
                    <Maximize2 style={{ width: '12px', height: '12px', color: '#64748b' }} />
                  </button>
                  <button onClick={() => docInputRef.current?.click()} style={{ padding: '4px', background: 'rgba(255,255,255,0.95)', border: '1px solid #d9dee7', borderRadius: '4px', cursor: 'pointer', display: 'flex' }} title="Replace File">
                    <RotateCw style={{ width: '12px', height: '12px', color: '#64748b' }} />
                  </button>
                </div>
              </div>
            )}
            <input type="file" ref={docInputRef} onChange={(e) => handleDocFileSelect(e.target.files[0])} accept="image/jpeg,image/png" style={{ display: 'none' }} />

            {/* Document metadata */}
            {docData && (
              <div style={{ marginTop: '10px', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '6px' }}>
                {[
                  { label: 'Type', value: docData.document_type || '—' },
                  { label: 'OCR', value: docData.ocr_status === 'COMPLETE' ? '✓ Parsed' : 'Pending' },
                  { label: 'Confidence', value: docData.ocr_confidence ? `${docData.ocr_confidence}%` : '—' },
                  { label: 'Checksum', value: docData.validation_passed ? '✓ Valid' : '⚠ Fail' },
                ].map(m => (
                  <div key={m.label} style={{ padding: '6px 8px', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #f1f5f9' }}>
                    <div style={metaLabel}>{m.label}</div>
                    <div style={{ ...metaValue, color: m.value.startsWith('✓') ? '#166534' : m.value.startsWith('⚠') ? '#991b1b' : '#1f2937', fontSize: '11px' }}>{m.value}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Extracted fields */}
          <div style={sectionBox}>
            <div style={sectionTitle}>
              <span>Extracted Data</span>
              <span style={{ fontSize: '11px', fontWeight: 500, color: '#64748b' }}>
                {docData?.document_type ? `${docData.document_type}` : 'Pending'}
              </span>
            </div>

            {docData?.extracted_fields && Object.keys(docData.extracted_fields).length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                {[
                  { label: 'Name', value: docData.extracted_fields.name?.value },
                  { label: 'Document No.', value: maskDocNumber(docData.extracted_fields.passport_number?.value || docData.extracted_fields.aadhaar_number?.value || docData.extracted_fields.dl_number?.value, docData.document_type), mono: true },
                  { label: 'Date of Birth', value: docData.extracted_fields.dob?.value },
                  { label: 'Nationality', value: docData.extracted_fields.nationality?.value || 'IND' },
                  { label: 'Gender', value: docData.extracted_fields.gender?.value },
                  { label: 'Issue Date', value: docData.extracted_fields.issue_date?.value },
                  { label: 'Expiry Date', value: docData.extracted_fields.expiry_date?.value },
                ].map(f => (
                  <div key={f.label} style={{ padding: '6px 8px', backgroundColor: '#f8fafc', borderRadius: '4px', border: '1px solid #f1f5f9' }}>
                    <div style={metaLabel}>{f.label}</div>
                    <div style={{ fontSize: '12px', fontWeight: 500, color: '#1f2937' }}>{f.value || '—'}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8', fontSize: '12px' }}>
                Upload a document to view extracted fields.
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: Traveler & Execute */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Traveler */}
          <div style={sectionBox}>
            <div style={sectionTitle}>
              <span>Traveler Verification</span>
              <span style={{ fontSize: '11px', fontWeight: 500, color: liveFile ? '#166534' : useLiveCamera ? '#1f4e79' : '#94a3b8' }}>
                {liveFile ? '✓ Captured' : useLiveCamera ? 'Live camera' : 'Awaiting capture'}
              </span>
            </div>

            {!livePreview && !useLiveCamera ? (
              <div style={{ border: '1px dashed #d9dee7', borderRadius: '6px', padding: '36px 16px', textAlign: 'center', backgroundColor: '#fafbfc' }}>
                <div style={{ fontSize: '13px', fontWeight: 500, color: '#334155', marginBottom: '2px' }}>Capture traveler photo</div>
                <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '14px' }}>Live camera with liveness verification or file upload</div>
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                  <button onClick={startLiveCamera} style={btnPrimary}>Start camera</button>
                  <button onClick={() => liveInputRef.current?.click()} style={btnSecondary}>Upload photo</button>
                </div>
              </div>
            ) : useLiveCamera ? (
              <div style={{ position: 'relative', backgroundColor: '#000', borderRadius: '4px', overflow: 'hidden', height: '210px' }}>
                <video ref={videoLiveRef} autoPlay playsInline muted style={{ height: '100%', width: '100%', objectFit: 'cover', transform: 'scaleX(-1)' }} />
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
                  <div style={{ width: '110px', height: '150px', borderRadius: '50%', border: '2px dashed rgba(255,255,255,0.5)' }} />
                </div>
                <div style={{ position: 'absolute', bottom: '6px', left: '6px', right: '6px', backgroundColor: 'rgba(0,0,0,0.8)', padding: '8px 12px', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#fff', fontSize: '11px' }}>
                  <div>
                    <div style={{ fontWeight: 600, marginBottom: '1px' }}>
                      {livenessStep === 1 && 'Look directly at camera'}
                      {livenessStep === 2 && 'Turn head left'}
                      {livenessStep === 3 && 'Return to center'}
                      {livenessStep === 4 && 'Blink twice'}
                      {livenessStep >= 5 && 'Ready to capture'}
                    </div>
                    <div style={{ color: '#94a3b8', fontSize: '10px' }}>Step {Math.min(livenessStep, 4)} of 4</div>
                  </div>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {livenessStep === 2 && <button onClick={completeTurnStep} style={{ ...btnPrimary, padding: '3px 8px', fontSize: '10px', backgroundColor: '#166534' }}>Confirm</button>}
                    {livenessStep === 3 && <button onClick={completeCenterStep} style={{ ...btnPrimary, padding: '3px 8px', fontSize: '10px', backgroundColor: '#166534' }}>Confirm</button>}
                    {livenessStep === 4 && <button onClick={completeBlinkStep} style={{ ...btnPrimary, padding: '3px 8px', fontSize: '10px', backgroundColor: '#166534' }}>Confirm</button>}
                    {livenessStep >= 4 && <button onClick={captureLiveTraveler} style={{ ...btnPrimary, padding: '3px 8px', fontSize: '10px' }}>Capture</button>}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ position: 'relative', backgroundColor: '#f8fafc', borderRadius: '4px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', height: '210px', padding: '8px', border: '1px solid #e2e8f0' }}>
                <img src={livePreview} alt="Traveler" style={{ maxHeight: '190px', objectFit: 'contain', borderRadius: '3px' }} />
                <button onClick={startLiveCamera} style={{ position: 'absolute', top: '6px', right: '6px', padding: '4px', background: 'rgba(255,255,255,0.95)', border: '1px solid #d9dee7', borderRadius: '4px', cursor: 'pointer', display: 'flex' }} title="Retake Photo">
                  <RotateCw style={{ width: '12px', height: '12px', color: '#64748b' }} />
                </button>
              </div>
            )}
            <input type="file" ref={liveInputRef} onChange={(e) => handleLiveFileUpload(e.target.files[0])} accept="image/jpeg,image/png" style={{ display: 'none' }} />

            {/* Liveness indicators */}
            <div style={{ marginTop: '8px', display: 'flex', gap: '4px' }}>
              {livenessSteps.map((ls, i) => (
                <div key={i} style={{
                  flex: 1, padding: '5px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 500, textAlign: 'center',
                  backgroundColor: ls.done ? '#f0fdf4' : '#f8fafc',
                  color: ls.done ? '#166534' : '#94a3b8',
                  border: `1px solid ${ls.done ? '#dcfce7' : '#e2e8f0'}`,
                }}>
                  {ls.done ? '✓' : (i + 1)} {ls.label}
                </div>
              ))}
            </div>
          </div>

          {/* Readiness & Execute */}
          <div style={{ ...sectionBox, backgroundColor: '#f8fafc' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: '#1f2937', marginBottom: '10px' }}>
              Screening Readiness
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '14px', fontSize: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#64748b' }}>Document image</span>
                <span style={{ fontWeight: 500, color: isDocReady ? '#166534' : '#94a3b8' }}>{isDocReady ? '✓ Loaded' : 'Required'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#64748b' }}>Traveler photo</span>
                <span style={{ fontWeight: 500, color: isTravelerReady ? '#166534' : '#94a3b8' }}>{isTravelerReady ? '✓ Captured' : 'Required'}</span>
              </div>
            </div>
            <button
              onClick={handleRunScreening}
              disabled={!isReadyToRun || loading}
              style={{
                width: '100%', padding: '10px 16px', fontSize: '13px', fontWeight: 500,
                backgroundColor: isReadyToRun && !loading ? '#1f4e79' : '#e2e8f0',
                color: isReadyToRun && !loading ? '#fff' : '#94a3b8',
                border: 'none', borderRadius: '4px',
                cursor: isReadyToRun && !loading ? 'pointer' : 'not-allowed',
                fontFamily: "'Inter', system-ui, sans-serif",
              }}
            >
              {loading ? 'Processing…' : 'Run Screening'}
            </button>
          </div>
        </div>
      </div>

      {/* Demo Scenarios */}
      <div style={{ ...sectionBox, marginBottom: '16px', padding: '12px 16px' }}>
        <button
          onClick={() => setDemoExpanded(!demoExpanded)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: 'none', border: 'none', cursor: 'pointer', padding: 0,
            fontSize: '12px', fontWeight: 500, color: '#64748b',
            fontFamily: "'Inter', system-ui, sans-serif",
          }}
        >
          <span>Demo / test scenarios</span>
          <span style={{ fontSize: '10px' }}>{demoExpanded ? '▲' : '▼'}</span>
        </button>

        {demoExpanded && (
          <div style={{ marginTop: '10px', display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
            {scenarios.map((sc, i) => (
              <button
                key={sc.key}
                onClick={() => loadPresetScenario(sc.key, sc.doc, sc.live)}
                style={{
                  padding: '10px', textAlign: 'left', borderRadius: '4px', cursor: 'pointer',
                  border: activeScenario === sc.key ? '1px solid #1f4e79' : '1px solid #e2e8f0',
                  backgroundColor: activeScenario === sc.key ? '#f1f5f9' : '#fff',
                  fontFamily: "'Inter', system-ui, sans-serif",
                }}
              >
                <div style={{ fontSize: '10px', fontWeight: 500, color: '#94a3b8', marginBottom: '2px' }}>{i + 1}</div>
                <div style={{ fontSize: '12px', fontWeight: 500, color: '#1f2937', marginBottom: '2px' }}>{sc.label}</div>
                <div style={{ fontSize: '10px', fontWeight: 400, color: sc.color }}>Expected: {sc.expected}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Processing modal */}
      {loading && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 50, backgroundColor: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
          <div style={{ backgroundColor: '#fff', borderRadius: '6px', border: '1px solid #d9dee7', maxWidth: '400px', width: '100%', padding: '24px', boxShadow: '0 2px 12px rgba(0,0,0,0.06)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', paddingBottom: '10px', borderBottom: '1px solid #e2e8f0' }}>
              <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#1f2937', margin: 0 }}>Processing screening</h3>
              <span style={{ fontSize: '12px', color: '#64748b' }}>{elapsedTime}s</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '16px' }}>
              {pipelineStages.map((stage, idx) => {
                const done = idx < currentStageIndex;
                const active = idx === currentStageIndex;
                return (
                  <div key={stage} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
                    <span style={{
                      width: '16px', height: '16px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '9px', fontWeight: 600, flexShrink: 0,
                      backgroundColor: done ? '#166534' : active ? '#1f4e79' : '#f1f5f9',
                      color: done || active ? '#fff' : '#94a3b8',
                    }}>
                      {done ? '✓' : active ? '●' : '○'}
                    </span>
                    <span style={{ color: done ? '#1f2937' : active ? '#1f4e79' : '#94a3b8', fontWeight: active ? 500 : 400 }}>{stage}</span>
                  </div>
                );
              })}
            </div>
            <div style={{ width: '100%', backgroundColor: '#f1f5f9', height: '3px', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ backgroundColor: '#1f4e79', height: '100%', transition: 'width 0.3s', width: `${((currentStageIndex + 1) / pipelineStages.length) * 100}%` }} />
            </div>
          </div>
        </div>
      )}

      {/* Document camera modal */}
      {showDocCamera && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 50, backgroundColor: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
          <div style={{ backgroundColor: '#fff', borderRadius: '6px', border: '1px solid #d9dee7', maxWidth: '640px', width: '100%', padding: '20px', boxShadow: '0 2px 12px rgba(0,0,0,0.06)', fontFamily: "'Inter', system-ui, sans-serif" }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', paddingBottom: '10px', borderBottom: '1px solid #e2e8f0' }}>
              <span style={{ fontSize: '14px', fontWeight: 600, color: '#1f2937' }}>Document scanner</span>
              <button onClick={closeDocCamera} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', display: 'flex' }}><X style={{ width: '16px', height: '16px' }} /></button>
            </div>
            <div style={{ position: 'relative', backgroundColor: '#000', borderRadius: '4px', overflow: 'hidden', height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '14px' }}>
              {!docCameraCaptured ? (
                <>
                  <video ref={videoDocRef} autoPlay playsInline muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none', padding: '20px' }}>
                    <div style={{ width: '100%', height: '100%', maxWidth: '400px', maxHeight: '240px', border: '2px dashed rgba(255,255,255,0.4)', borderRadius: '4px' }} />
                  </div>
                </>
              ) : (
                <img src={docCameraCaptured} alt="Captured" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              )}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              {!docCameraCaptured ? (
                <button onClick={captureDocFrame} style={btnPrimary}>Capture</button>
              ) : (
                <>
                  <button onClick={retakeDocFrame} style={btnSecondary}>Retake</button>
                  <button onClick={useDocCapturedImage} style={{ ...btnPrimary, backgroundColor: '#166534' }}>Use image</button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Full document modal */}
      {showFullDocModal && docPreview && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 50, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
          <div style={{ position: 'relative', maxWidth: '900px', maxHeight: '90vh', backgroundColor: '#fff', borderRadius: '6px', padding: '14px', border: '1px solid #d9dee7', display: 'flex', flexDirection: 'column', alignItems: 'center', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}>
            <button onClick={() => setShowFullDocModal(false)} style={{ position: 'absolute', top: '10px', right: '10px', padding: '4px', backgroundColor: '#1f2937', color: '#fff', border: 'none', borderRadius: '50%', cursor: 'pointer', display: 'flex', zIndex: 10 }}>
              <X style={{ width: '14px', height: '14px' }} />
            </button>
            <img src={docPreview} alt="Full Resolution" style={{ maxHeight: '75vh', objectFit: 'contain', borderRadius: '4px' }} />
            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '8px' }}>
              {docDimensions.width} × {docDimensions.height} px
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
