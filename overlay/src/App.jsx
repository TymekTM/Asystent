import React, { useState, useEffect } from 'react';
import { listen } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/tauri';
import './style.css'; // Ensure this is importing the updated style.css

const App = () => {
  // const [status, setStatus] = useState('idle'); // Raw status string from backend
  const [text, setText] = useState('');
  const [isVisible, setIsVisible] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [wakeWordDetected, setWakeWordDetected] = useState(false);
  const [showBall, setShowBall] = useState(false);

  useEffect(() => {
    console.log('[React] App starting, setting up state and listeners');
    
    // Add keyboard shortcut for opening devtools
    const handleKeyDown = (event) => {
      if (event.key === 'F12' || (event.ctrlKey && event.shiftKey && event.key === 'I')) {
        console.log('[React] Opening devtools');
        invoke('open_devtools').catch(console.error);
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);

    invoke('get_state').then(initialState => {
      console.log('[React] Initial state received:', initialState);
      // setStatus(initialState.status);
      setText(initialState.text);
      setIsVisible(initialState.visible);
      setIsListening(initialState.is_listening);
      setIsSpeaking(initialState.is_speaking);
      setWakeWordDetected(initialState.wake_word_detected);
    });    const unlisten = listen('status-update', (event) => {
      console.log('[React] Status update received:', event.payload);
      const payload = event.payload;
      
      setText(payload.text);
      setIsListening(payload.is_listening);
      setIsSpeaking(payload.is_speaking);
      setWakeWordDetected(payload.wake_word_detected);
      
      // Enhanced visibility logic - show if any activity or meaningful content
      const hasActivity = payload.is_listening || payload.is_speaking || payload.wake_word_detected;
      const hasMeaningfulContent = payload.text && payload.text !== '' && 
                                  payload.text !== 'Listening...' && 
                                  payload.text !== 'Offline';
      const shouldBeVisible = hasActivity || hasMeaningfulContent;
      
      console.log('[React] Visibility calculation:', {
        hasActivity,
        hasMeaningfulContent,
        shouldBeVisible,
        text: payload.text
      });
      
      setIsVisible(shouldBeVisible);
    });

    return () => {
      unlisten.then(f => f());
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);
  // Trigger ball animation when overlay becomes active
  useEffect(() => {
    if (isListening || isSpeaking || wakeWordDetected) {
      setShowBall(true);
    } else {
      // Hide ball when activity ends
      setShowBall(false);
    }
  }, [isListening, isSpeaking, wakeWordDetected]);
  // Determine current display status string for UI
  let displayStatusText = '';
  let animationClass = '';

  if (isSpeaking) {
    displayStatusText = 'Odpowiadam...';
    animationClass = 'speaking-animation';
  } else if (isListening) {
    displayStatusText = 'Słucham...';
    animationClass = 'listening-animation';
  } else if (wakeWordDetected) {
    displayStatusText = 'Przetwarzam...';
    animationClass = 'wakeword-animation';
  }// Render content always - Rust manages window visibility
  // React only focuses on displaying the correct content based on state  // Helper function to get dynamic font size class based on text length
  const getTextSizeClass = (text) => {
    if (!text) return '';
    const length = text.length;
    
    if (length <= 50) return 'short-text';
    if (length <= 150) return 'medium-text';
    if (length <= 300) return 'long-text';
    return 'very-long-text';
  };

  // Helper function to get icon based on status
  const getStatusIcon = () => {
    if (isSpeaking) return "🔊"; // Speaker icon
    if (isListening) return "🎤"; // Microphone icon
    if (wakeWordDetected) return "👂"; // Ear icon
    return "";
  };return (
    <div className={`overlay-container ${animationClass}`}>
      {/* Gray gradient background when overlay is active */}
      {(isListening || isSpeaking || wakeWordDetected) && (
        <div className="overlay-background"></div>
      )}      {/* Animated Gaja ball */}
      <div className={`gaja-ball ${showBall ? 'active' : 'hidden'}`}>
        <div className="gaja-ball-inner">
          {/* Ball has animated waves from CSS - no smile needed */}
        </div>
      </div>

      {/* Status text below the ball */}
      {(isListening || isSpeaking || wakeWordDetected) && displayStatusText && (
        <div className="gaja-status-text">
          {displayStatusText}
        </div>
      )}
        {/* Response text with dynamic font size */}
      {text && (
        <div className={`gaja-response-text ${getTextSizeClass(text)}`}>
          <p>{text}</p>
        </div>
      )}
    </div>
  );
};

export default App;
