"""
VoiceForge AI - Speech Recognition Module
Infinity Code Hackathon - Stark Industries Challenge

Advanced speech recognition system supporting Hindi and English
with noise reduction and offline capabilities.
"""

import asyncio
import logging
import numpy as np
import speech_recognition as sr
import whisper
import pyaudio
import wave
import io
import threading
from typing import Optional, Dict, List
from datetime import datetime

from ..utils.config_manager import ConfigManager


class SpeechRecognizer:
    """Advanced speech recognition with bilingual support"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize speech recognition components
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.whisper_model = None
        
        # Audio processing settings
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.channels = 1
        self.audio_format = pyaudio.paInt16
        
        # Recognition settings
        self.energy_threshold = 300
        self.pause_threshold = 0.8
        self.phrase_time_limit = 10
        self.timeout = 2
        
        # Language settings
        self.primary_language = config.get("language", "en")
        self.offline_mode = config.get("offline_mode", False)
        
        # Audio buffer for continuous recognition
        self.audio_buffer = []
        self.is_recording = False
        self.audio_thread = None
        
        # Performance metrics
        self.recognition_stats = {
            "total_attempts": 0,
            "successful_recognitions": 0,
            "failed_recognitions": 0,
            "average_confidence": 0.0
        }
        
        self.logger.info("SpeechRecognizer initialized")
    
    async def initialize(self) -> bool:
        """Initialize the speech recognition system"""
        try:
            # Initialize microphone
            self.microphone = sr.Microphone(sample_rate=self.sample_rate)
            
            # Configure recognizer
            with self.microphone as source:
                self.logger.info("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            self.recognizer.energy_threshold = self.energy_threshold
            self.recognizer.pause_threshold = self.pause_threshold
            self.recognizer.dynamic_energy_threshold = True
            
            # Initialize Whisper for offline mode
            if self.offline_mode:
                await self._initialize_whisper()
            
            self.logger.info("Speech recognition system initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize speech recognizer: {e}")
            return False
    
    async def _initialize_whisper(self):
        """Initialize Whisper model for offline recognition"""
        try:
            self.logger.info("Loading Whisper model for offline recognition...")
            # Load model in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            self.whisper_model = await loop.run_in_executor(
                None, whisper.load_model, "base"
            )
            self.logger.info("Whisper model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load Whisper model: {e}")
            self.offline_mode = False
    
    async def capture_audio(self) -> Optional[sr.AudioData]:
        """Capture audio from microphone with noise filtering"""
        try:
            if not self.microphone:
                self.logger.error("Microphone not initialized")
                return None
            
            with self.microphone as source:
                # Listen for audio with timeout and phrase limit
                audio = self.recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=self.phrase_time_limit
                )
                
                # Apply noise reduction
                audio = self._apply_noise_reduction(audio)
                
                return audio
                
        except sr.WaitTimeoutError:
            # Normal timeout, not an error
            return None
        except Exception as e:
            self.logger.error(f"Error capturing audio: {e}")
            return None
    
    def _apply_noise_reduction(self, audio_data: sr.AudioData) -> sr.AudioData:
        """Apply noise reduction to audio data"""
        try:
            # Convert to numpy array for processing
            audio_np = np.frombuffer(audio_data.get_raw_data(), dtype=np.int16)
            
            # Apply simple noise gate
            noise_threshold = np.percentile(np.abs(audio_np), 10)
            audio_np = np.where(np.abs(audio_np) > noise_threshold, audio_np, 0)
            
            # Apply smoothing filter
            from scipy import signal
            b, a = signal.butter(4, 0.3, btype='low')
            audio_filtered = signal.filtfilt(b, a, audio_np.astype(float))
            
            # Convert back to audio data
            audio_filtered = audio_filtered.astype(np.int16)
            raw_data = audio_filtered.tobytes()
            
            return sr.AudioData(raw_data, audio_data.sample_rate, audio_data.sample_width)
            
        except ImportError:
            # Scipy not available, return original audio
            self.logger.warning("Scipy not available for noise reduction")
            return audio_data
        except Exception as e:
            self.logger.error(f"Error in noise reduction: {e}")
            return audio_data
    
    async def transcribe_audio(self, audio_data: sr.AudioData) -> Optional[str]:
        """Transcribe audio data to text"""
        if not audio_data:
            return None
        
        self.recognition_stats["total_attempts"] += 1
        
        try:
            if self.offline_mode and self.whisper_model:
                return await self._transcribe_offline(audio_data)
            else:
                return await self._transcribe_online(audio_data)
                
        except Exception as e:
            self.logger.error(f"Error transcribing audio: {e}")
            self.recognition_stats["failed_recognitions"] += 1
            return None
    
    async def _transcribe_online(self, audio_data: sr.AudioData) -> Optional[str]:
        """Online transcription using Google Speech Recognition"""
        try:
            # Try primary language first
            if self.primary_language == "hi":
                try:
                    text = self.recognizer.recognize_google(
                        audio_data, 
                        language="hi-IN",
                        show_all=False
                    )
                    if text.strip():
                        self.recognition_stats["successful_recognitions"] += 1
                        self.logger.info(f"Recognized (Hindi): '{text}'")
                        return text.strip()
                except sr.UnknownValueError:
                    pass  # Try English fallback
            
            # Try English recognition
            text = self.recognizer.recognize_google(
                audio_data, 
                language="en-US",
                show_all=False
            )
            
            if text.strip():
                self.recognition_stats["successful_recognitions"] += 1
                self.logger.info(f"Recognized (English): '{text}'")
                return text.strip()
            
            return None
            
        except sr.UnknownValueError:
            self.logger.debug("Could not understand audio")
            self.recognition_stats["failed_recognitions"] += 1
            return None
        except sr.RequestError as e:
            self.logger.error(f"Speech recognition service error: {e}")
            self.recognition_stats["failed_recognitions"] += 1
            return None
    
    async def _transcribe_offline(self, audio_data: sr.AudioData) -> Optional[str]:
        """Offline transcription using Whisper"""
        try:
            # Convert audio data to format expected by Whisper
            audio_np = np.frombuffer(
                audio_data.get_raw_data(), 
                dtype=np.int16
            ).astype(np.float32) / 32768.0
            
            # Resample if necessary
            if audio_data.sample_rate != 16000:
                import librosa
                audio_np = librosa.resample(
                    audio_np, 
                    orig_sr=audio_data.sample_rate, 
                    target_sr=16000
                )
            
            # Run Whisper transcription in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self.whisper_model.transcribe, 
                audio_np
            )
            
            text = result["text"].strip()
            if text:
                self.recognition_stats["successful_recognitions"] += 1
                self.logger.info(f"Recognized (Whisper): '{text}'")
                return text
            
            return None
            
        except Exception as e:
            self.logger.error(f"Whisper transcription error: {e}")
            self.recognition_stats["failed_recognitions"] += 1
            return None
    
    def start_continuous_recognition(self, callback):
        """Start continuous audio recognition in background"""
        if self.is_recording:
            self.logger.warning("Continuous recognition already running")
            return
        
        self.is_recording = True
        self.audio_thread = threading.Thread(
            target=self._continuous_recognition_thread,
            args=(callback,),
            daemon=True
        )
        self.audio_thread.start()
        self.logger.info("Started continuous recognition")
    
    def stop_continuous_recognition(self):
        """Stop continuous audio recognition"""
        self.is_recording = False
        if self.audio_thread:
            self.audio_thread.join(timeout=2)
        self.logger.info("Stopped continuous recognition")
    
    def _continuous_recognition_thread(self, callback):
        """Background thread for continuous recognition"""
        while self.is_recording:
            try:
                # Use asyncio.run to handle async capture and transcription
                audio_data = asyncio.run(self.capture_audio())
                if audio_data:
                    text = asyncio.run(self.transcribe_audio(audio_data))
                    if text:
                        callback(text)
            except Exception as e:
                self.logger.error(f"Error in continuous recognition: {e}")
                time.sleep(1)  # Prevent busy loop on errors
    
    def set_language(self, language: str):
        """Set the primary recognition language"""
        self.primary_language = language
        self.logger.info(f"Primary language set to: {language}")
    
    def set_offline_mode(self, offline: bool):
        """Enable or disable offline mode"""
        if offline and not self.whisper_model:
            asyncio.create_task(self._initialize_whisper())
        
        self.offline_mode = offline
        self.logger.info(f"Offline mode: {'enabled' if offline else 'disabled'}")
    
    def adjust_sensitivity(self, sensitivity: float):
        """Adjust microphone sensitivity (0.0 to 1.0)"""
        self.energy_threshold = int(4000 * (1.0 - sensitivity))
        self.recognizer.energy_threshold = self.energy_threshold
        self.logger.info(f"Sensitivity adjusted to {sensitivity} (threshold: {self.energy_threshold})")
    
    def get_recognition_stats(self) -> Dict:
        """Get recognition performance statistics"""
        total = self.recognition_stats["total_attempts"]
        success_rate = (
            self.recognition_stats["successful_recognitions"] / total
            if total > 0 else 0
        )
        
        return {
            **self.recognition_stats,
            "success_rate": success_rate,
            "current_language": self.primary_language,
            "offline_mode": self.offline_mode
        }
    
    def test_microphone(self) -> Dict:
        """Test microphone functionality"""
        try:
            if not self.microphone:
                return {"success": False, "error": "Microphone not initialized"}
            
            # Test audio capture
            with self.microphone as source:
                self.logger.info("Testing microphone... (speak now)")
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=2)
            
            # Calculate audio levels
            audio_data = np.frombuffer(audio.get_raw_data(), dtype=np.int16)
            rms_level = np.sqrt(np.mean(audio_data ** 2))
            max_level = np.max(np.abs(audio_data))
            
            return {
                "success": True,
                "rms_level": float(rms_level),
                "max_level": float(max_level),
                "sample_rate": audio.sample_rate,
                "duration": len(audio_data) / audio.sample_rate
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up speech recognizer...")
        
        self.stop_continuous_recognition()
        
        if hasattr(self, 'whisper_model') and self.whisper_model:
            del self.whisper_model
        
        self.logger.info("Speech recognizer cleanup completed")
    
    def stop(self):
        """Stop the speech recognizer"""
        self.stop_continuous_recognition()
        self.is_recording = False