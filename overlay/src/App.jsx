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

  useEffect(() => {
    invoke('get_state').then(initialState => {
      // setStatus(initialState.status);
      setText(initialState.text);
      setIsVisible(initialState.visible);
      setIsListening(initialState.is_listening);
      setIsSpeaking(initialState.is_speaking);
      setWakeWordDetected(initialState.wake_word_detected);
    });

    const unlisten = listen('status-update', (event) => {
      const payload = event.payload;
      // setStatus(payload.status); // The specific booleans are more useful for UI state
      setText(payload.text);
      setIsListening(payload.is_listening);
      setIsSpeaking(payload.is_speaking);
      setWakeWordDetected(payload.wake_word_detected);

      // Visibility logic primarily handled by Rust based on activity.
      // This syncs the React state for rendering.
      if (payload.is_listening || payload.is_speaking || payload.wake_word_detected || payload.text !== '') {
        setIsVisible(true);
      } else {
        setIsVisible(false);
      }
    });

    return () => {
      unlisten.then(f => f());
    };
  }, []);

  // Determine current display status string for UI
  let displayStatusText = '';
  let animationClass = '';

  if (isSpeaking) {
    displayStatusText = 'Mówię...';
    animationClass = 'speaking-animation';
  } else if (isListening) {
    displayStatusText = 'Słucham...';
    animationClass = 'listening-animation';
  } else if (wakeWordDetected) {
    displayStatusText = 'Słucham po wake word...'; // More descriptive for wake word active state
    animationClass = 'wakeword-animation';
  }

  // Render logic: if not visible AND there is no text to display (e.g., fading out), render null.
  // If there IS text, we might want to show it even if other activity flags are false (e.g., assistant finished speaking)
  if (!isVisible && text === '') {
    return null;
  }

  return (
    <div className={`overlay-container ${animationClass}`}>
      {(isListening || isSpeaking || wakeWordDetected) && displayStatusText && (
        <div className={`status-indicator ${isSpeaking ? 'speaking' : isListening ? 'listening' : 'wakeword'}`}>
          {displayStatusText}
        </div>
      )}
      
      {text && (
        <div className="text-display gaja-welcome">
          {/* Using gaja-welcome for styling the main text bubble */}
          <p>{text}</p>
        </div>
      )}
    </div>
  );
};

export default App;
