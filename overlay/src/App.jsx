import React, { useState, useEffect } from 'react';
import { listen } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/tauri';
import './style.css'; // Import the CSS file

const App = () => {
  const [status, setStatus] = useState('idle'); // idle, listening, speaking, wake_word
  const [text, setText] = useState('');
  const [isVisible, setIsVisible] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [wakeWordDetected, setWakeWordDetected] = useState(false);

  useEffect(() => {
    // Get initial state
    invoke('get_state').then(initialState => {
      setStatus(initialState.status);
      setText(initialState.text);
      setIsVisible(initialState.visible);
      setIsListening(initialState.is_listening);
      setIsSpeaking(initialState.is_speaking);
      setWakeWordDetected(initialState.wake_word_detected);
    });

    const unlisten = listen('status-update', (event) => {
      const payload = event.payload;
      setStatus(payload.status);
      setText(payload.text);
      setIsListening(payload.is_listening);
      setIsSpeaking(payload.is_speaking);
      setWakeWordDetected(payload.wake_word_detected);

      // Determine visibility based on state
      if (payload.is_listening || payload.is_speaking || payload.wake_word_detected) {
        setIsVisible(true);
      } else if (payload.text === '' && !payload.is_listening && !payload.is_speaking && !payload.wake_word_detected) {
        // Hide if idle and no text is present (after a delay might be better)
        // For now, direct hide if no activity and no text.
        // A timer in Rust side handles hiding after inactivity, this is a fallback/sync
        setIsVisible(false);
      } else if (payload.text !== '') {
        setIsVisible(true); // Keep visible if there's text
      }
    });

    return () => {
      unlisten.then(f => f());
    };
  }, []);

  if (!isVisible && text === '') {
    return null; // Don't render anything if not visible and no text
  }
  
  let animationClass = '';
  if (isSpeaking) {
    animationClass = 'speaking-animation';
  } else if (isListening) {
    animationClass = 'listening-animation';
  } else if (wakeWordDetected) {
    animationClass = 'wakeword-animation';
  }


  return (
    <div className={`overlay-container ${animationClass}`}>
      {isListening && <div className="status-indicator listening">Słucham...</div>}
      {isSpeaking && <div className="status-indicator speaking">Mówię...</div>}
      {wakeWordDetected && !isListening && !isSpeaking && <div className="status-indicator wakeword">Wykryto wake word!</div>}
      
      {text && (
        <div className="text-display">
          {text}
        </div>
      )}
    </div>
  );
};

export default App;
