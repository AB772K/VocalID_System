import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mic, Square, Play, CheckCircle, XCircle, Clock, LogOut, Info} from 'lucide-react';
import '../styles/VoiceChallenge.css';

const VoiceChallenge = () => {
  const [user, setUser] = useState(null);
  const [challenge, setChallenge] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordedAudio, setRecordedAudio] = useState(null);
  const [verificationStatus, setVerificationStatus] = useState(null);
  const [verificationDetails, setVerificationDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [timeLeft, setTimeLeft] = useState(300); // 5 minutes in seconds
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorder = useRef(null);
  const audioChunks = useRef([]);
  const streamRef = useRef(null);
  const navigate = useNavigate();
  const recordingIntervalRef = useRef(null);

  // Get user from localStorage
  useEffect(() => {
    const userData = localStorage.getItem('auth_user');
    if (!userData) {
      navigate('/voice-login');
      return;
    }
    const parsedUser = JSON.parse(userData);
    setUser(parsedUser);
    generateNewChallenge(parsedUser.user_id);
  }, [navigate]);

  // Challenge countdown
  useEffect(() => {
    if (!challenge || timeLeft <= 0) return;
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          handleChallengeExpired();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [challenge, timeLeft]);

  const generateNewChallenge = async (userId) => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/auth/generate-challenge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      if (!response.ok) throw new Error('Failed to generate challenge');
      const data = await response.json();
      setChallenge(data);
      setTimeLeft(300); // Reset to 5 minutes
      setVerificationStatus(null);
      setRecordedAudio(null);
      setVerificationDetails(null);
      setRecordingTime(0);
    } catch (error) {
      console.error('Error generating challenge:', error);
      alert('Failed to generate authentication challenge');
    } finally {
      setLoading(false);
    }
  };

  const handleChallengeExpired = () => {
    setVerificationStatus('expired');
    setRecordedAudio(null);
    // Auto-generate new challenge after 2 seconds
    setTimeout(() => {
      if (user) generateNewChallenge(user.user_id);
    }, 2000);
  };

  const startRecording = async () => {
    try {
      setRecordedAudio(null);
      setRecordingTime(0);
      setVerificationStatus(null);
      setVerificationDetails(null);
      audioChunks.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { 
          echoCancellation: true, 
          noiseSuppression: true, 
          sampleRate: 16000,
          channelCount: 1 
        },
      });

      streamRef.current = stream;
      
      // Use WebM for better browser compatibility
      const options = { mimeType: 'audio/webm;codecs=opus' };
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        console.warn('WebM with Opus not supported, using default');
        mediaRecorder.current = new MediaRecorder(stream);
      } else {
        mediaRecorder.current = new MediaRecorder(stream, options);
      }

      mediaRecorder.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.current.push(event.data);
        }
      };

      mediaRecorder.current.onstop = () => {
        console.log('MediaRecorder stopped, creating audio blob...');
        try {
          const audioBlob = new Blob(audioChunks.current, { type: 'audio/wav' });
          const audioUrl = URL.createObjectURL(audioBlob);
          setRecordedAudio({ blob: audioBlob, url: audioUrl });
          console.log('Audio recording created successfully');
        } catch (error) {
          console.error('Error creating audio blob:', error);
        }

        // Clean up stream
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => {
            track.stop();
          });
          streamRef.current = null;
        }

        setIsRecording(false);
        
        // Clear recording interval
        if (recordingIntervalRef.current) {
          clearInterval(recordingIntervalRef.current);
          recordingIntervalRef.current = null;
        }
      };

      // Start recording with 100ms chunks for better responsiveness
      mediaRecorder.current.start(100);
      setIsRecording(true);
      console.log('Recording started');

      // Update recording timer (just for display, no auto-stop)
      recordingIntervalRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Cannot access microphone. Please check permissions and try again.');
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    console.log('🛑 Stopping recording...');
    
    // Clear the recording timer
    if (recordingIntervalRef.current) {
      clearInterval(recordingIntervalRef.current);
      recordingIntervalRef.current = null;
    }

    // Stop media recorder if it's recording
    if (mediaRecorder.current && mediaRecorder.current.state === 'recording') {
      console.log('Stopping MediaRecorder...');
      try {
        mediaRecorder.current.stop();
      } catch (e) {
        console.error('Error stopping MediaRecorder:', e);
        // Force cleanup if stop fails
        cleanupAfterRecording();
      }
    } else {
      console.log('MediaRecorder not in recording state, forcing cleanup');
      cleanupAfterRecording();
    }
  };

  const cleanupAfterRecording = () => {
    // Stop stream tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        track.stop();
      });
      streamRef.current = null;
    }

    setIsRecording(false);

    // Create audio from chunks if we have any
    if (audioChunks.current.length > 0 && !recordedAudio) {
      console.log('Creating audio from existing chunks...');
      try {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        setRecordedAudio({ blob: audioBlob, url: audioUrl });
      } catch (error) {
        console.error('Error creating audio from chunks:', error);
      }
    }
  };

  const playRecording = () => {
    if (recordedAudio && recordedAudio.url) {
      const audio = new Audio(recordedAudio.url);
      audio.play().catch(e => console.error('Error playing audio:', e));
    }
  };

  const verifyRecording = async () => {
    if (!recordedAudio || !challenge || !user) {
      alert('Please record audio first');
      return;
    }
    
    setLoading(true);
    setVerificationStatus('verifying');
    
    try {
      const audioFile = new File([recordedAudio.blob], `challenge_${user.user_id}.wav`, { 
        type: 'audio/wav' 
      });
      
      const formData = new FormData();
      formData.append('audio_file', audioFile);
      formData.append('challenge_id', challenge.challenge_id);
      formData.append('user_id', user.user_id.toString());

      console.log('Sending verification request...');
      const response = await fetch('http://localhost:8000/auth/verify-challenge-enhanced', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Verification result:', result);
      
      if (result.success) {
        setVerificationStatus('success');
        setVerificationDetails(result.text_verification);
        localStorage.setItem('user', JSON.stringify(user));
        localStorage.removeItem('auth_user');
        
        setTimeout(() => navigate('/user/dashboard'), 2000);
      } else {
        setVerificationStatus('failed');
        setVerificationDetails(result.text_verification);
      }
    } catch (error) {
      console.error('Verification error:', error);
      setVerificationStatus('error');
      alert('Verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    // Clean up resources
    if (isRecording) {
      stopRecording();
    }
    localStorage.removeItem('auth_user');
    navigate('/voice-login');
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  if (!user) return <div className="voice-challenge loading">Loading user information...</div>;
  if (loading && !challenge) return <div className="voice-challenge loading">Preparing authentication challenge...</div>;
  if (!challenge) return <div className="voice-challenge error">Failed to load challenge. Please try again.</div>;

  return (
    <div className="voice-challenge">
      <div className="challenge-header">
        <div className="user-info">
          <h2>Voice Authentication</h2>
          <p>Welcome, <strong>{user.full_name}</strong></p>
          <p className="user-id">User ID: {user.user_id}</p>
        </div>
        <button onClick={handleCancel} className="cancel-btn">
          <LogOut size={16} /> Cancel
        </button>
      </div>

      <div className="challenge-card">
        <div className="challenge-phrase">
          <div className="phrase-label">Speak this phrase clearly:</div>
          <div className="phrase-text">{challenge.phrase}</div>
          <div className="time-remaining">
            <Clock size={16} /> 
            Challenge expires in: <strong>{formatTime(timeLeft)}</strong>
          </div>
        </div>

        {/* Recording Section */}
        <div className="recording-section">
          {!isRecording && !recordedAudio && timeLeft > 0 && (
            <div className="recording-controls">
              <button onClick={startRecording} className="record-btn start">
                <Mic size={20} /> Start Recording
              </button>
              <p className="recording-tip">Click to start speaking the phrase above</p>
            </div>
          )}

          
          {isRecording && (
            <div className="recording-active">
              <div className="recording-indicator">
                <div className="pulse"></div>
                <span>Recording in progress... Speak now!</span>
              </div>
              <div className="recording-time">
                <Clock size={16} />
                <span>Recording time: {formatTime(recordingTime)}</span>
              </div>
              <button onClick={stopRecording} className="record-btn stop">
                <Square size={20} /> Stop Recording
              </button>
              <p className="recording-tip">Click stop when you finish speaking the phrase</p>
            </div>
          )}
          

          {recordedAudio && !isRecording && timeLeft > 0 && (
            <div className="playback-section">
              <div className="playback-controls">
                <button onClick={playRecording} className="control-btn play">
                  <Play size={16} /> Play Recording
                </button>
                <button 
                  onClick={verifyRecording} 
                  disabled={loading} 
                  className="control-btn verify"
                >
                  {loading ? (
                    <>
                      <div className="spinner"></div>
                      Verifying...
                    </>
                  ) : (
                    'Verify Identity'
                  )}
                </button>
                <button 
                  onClick={() => {
                    setRecordedAudio(null);
                    setVerificationStatus(null);
                    setVerificationDetails(null);
                    setRecordingTime(0);
                  }} 
                  className="control-btn retry"
                >
                  Record Again
                </button>
              </div>
              <p className="recording-tip">Listen to your recording, then verify or record again</p>
            </div>
          )}

          {timeLeft === 0 && (
            <div className="expired-section">
              <p>Challenge expired. Please generate a new one.</p>
              <button 
                onClick={() => generateNewChallenge(user.user_id)} 
                className="control-btn retry"
              >
                Generate New Challenge
              </button>
            </div>
          )}
        </div>

        {/* Verification Status */}
        {verificationStatus && (
          <div className={`verification-status ${verificationStatus}`}>
            {verificationStatus === 'success' && (
              <><CheckCircle size={20} /><span>Authentication successful! Redirecting to dashboard...</span></>
            )}
            {verificationStatus === 'failed' && (
              <><XCircle size={20} /><span>Verification failed. Please try again.</span></>
            )}
            {verificationStatus === 'error' && (
              <><XCircle size={20} /><span>Authentication error. Please try again.</span></>
            )}
            {verificationStatus === 'verifying' && (
              <><div className="spinner"></div><span>Verifying your voice...</span></>
            )}
            {verificationStatus === 'expired' && (
              <><XCircle size={20} /><span>Challenge expired. Generating new challenge...</span></>
            )}
          </div>
        )}

        {/* Verification Details */}
        {verificationDetails && (
          <div className="verification-details">
            <div className="details-header">
              <Info size={16} />
              <span>Verification Details</span>
            </div>
            <div className="details-content">
              <div className="detail-item">
                <span className="label">Original Phrase:</span>
                <span className="value">{verificationDetails.original_phrase}</span>
              </div>
              <div className="detail-item">
                <span className="label">Spoken Text:</span>
                <span className="value">{verificationDetails.spoken_text || 'No speech detected'}</span>
              </div>
              <div className="detail-item">
                <span className="label">Similarity Score:</span>
                <span className="value">
                  {verificationDetails.similarity_score ? 
                    `${(verificationDetails.similarity_score * 100).toFixed(1)}%` : 'N/A'}
                </span>
              </div>
              <div className="detail-item">
                <span className="label">Required Score:</span>
                <span className="value">
                  {verificationDetails.confidence_threshold ? 
                    `${(verificationDetails.confidence_threshold * 100).toFixed(1)}%` : '80%'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="security-info">
        <h4>🔒 Secure Voice Authentication</h4>
        <ul>
          <li>✅ Dynamic phrase prevents replay attacks</li>
          <li>✅ OpenAI Whisper for accurate speech recognition</li>
          <li>✅ Real-time text verification</li>
          <li>✅ 5-minute session security</li>
          <li>✅ Voice biometrics integration (Phase B)</li>
        </ul>
      </div>
    </div>
  );
};

export default VoiceChallenge;