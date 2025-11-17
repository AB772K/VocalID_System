import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, User, Voicemail, Mic, List } from 'lucide-react';
import VoiceRecorder from '../components/VoiceRecorder';
import { authAPI } from '../services/api';
import '../styles/Dashboard.css';

const UserDashboard = () => {
  const [user, setUser] = useState(null);
  const [enrollments, setEnrollments] = useState([]);
  const [activeTab, setActiveTab] = useState('enrollments'); // Default to enrollments since record tab removed
  const [loadingEnrollments, setLoadingEnrollments] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (!userData) {
      navigate('/user/login');
      return;
    }
    const userObj = JSON.parse(userData);
    setUser(userObj);
    fetchEnrollments(userObj.user_id);
  }, [navigate]);

  const fetchEnrollments = async (userId) => {
    if (!userId) return;
    setLoadingEnrollments(true);
    try {
      const response = await authAPI.getUserEnrollments(userId);
      setEnrollments(response.enrollments || []);
    } catch (err) {
      console.error('Failed to load enrollments:', err);
      setEnrollments([]);
    } finally {
      setLoadingEnrollments(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('user');
    navigate('/voice-login');
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Invalid Date';
    }
  };

  if (!user) return <div className="loading">Loading...</div>;

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-left">
          <Voicemail className="logo-icon" />
          <h1>VocalID User Portal</h1>
        </div>
        <div className="header-right">
          <span>Welcome, {user.full_name}</span>
          <button onClick={handleLogout} className="logout-btn">
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </header>

      <div className="dashboard-content">
        <div className="card">
          <div className="card-header">
            <User className="card-icon" />
            <h2>User Information</h2>
          </div>
          <div style={{ padding: '30px' }}>
            <div className="user-info" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '15px' }}>
              <div>
                <strong>User ID:</strong> {user.user_id}
              </div>
              <div>
                <strong>Full Name:</strong> {user.full_name}
              </div>
              <div>
                <strong>Voice Enrollments:</strong> {enrollments.length}
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <List className="card-icon" />
            <h2>My Voice Enrollments</h2>
          </div>

          <div className="tab-content">
            <div className="enrollments-list">
              {loadingEnrollments ? (
                <div className="loading-enrollments">Loading enrollments...</div>
              ) : enrollments.length === 0 ? (
                <p className="no-data">
                  No voice enrollments yet.
                </p>
              ) : (
                enrollments.map((enrollment) => (
                  <div key={enrollment.audio_id} className="enrollment-item">
                    <div className="enrollment-info">
                      <div className="enrollment-id">
                        <strong>Audio ID:</strong> {enrollment.audio_id}
                      </div>
                      <div className="enrollment-date">Created: {formatDate(enrollment.created_at)}</div>
                    </div>
                    <div className="enrollment-actions">
                      <span className="enrollment-status">✅ Saved</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserDashboard;
