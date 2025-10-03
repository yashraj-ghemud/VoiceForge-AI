"""
VoiceForge AI - Core Voice Engine
Infinity Code Hackathon - Stark Industries Challenge

This module contains the main voice processing engine that coordinates
speech recognition, NLP processing, and command execution.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

from .speech_recognition import SpeechRecognizer
from .nlp_processor import NLPProcessor
from .automation_engine import AutomationEngine
from ..utils.config_manager import ConfigManager


class VoiceEngine:
    """Main voice processing engine coordinating all components"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.speech_recognizer = SpeechRecognizer(config)
        self.nlp_processor = NLPProcessor(config)
        self.automation_engine = AutomationEngine(config)
        
        # State management
        self.is_listening = False
        self.is_processing = False
        self.current_context = {}
        self.command_history = []
        self.session_id = str(int(time.time()))
        
        # Performance metrics
        self.metrics = {
            "commands_processed": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "average_response_time": 0.0,
            "session_start": datetime.now()
        }
        
        # Command queue for async processing
        self.command_queue = asyncio.Queue()
        self.response_callbacks = []
        
        self.logger.info(f"VoiceEngine initialized with session ID: {self.session_id}")
    
    async def start_listening(self) -> bool:
        """Start the voice recognition system"""
        if self.is_listening:
            self.logger.warning("Voice engine is already listening")
            return True
        
        try:
            # Initialize speech recognizer
            if not await self.speech_recognizer.initialize():
                self.logger.error("Failed to initialize speech recognizer")
                return False
            
            self.is_listening = True
            self.logger.info("Voice engine started listening")
            
            # Start the main processing loop
            asyncio.create_task(self._main_processing_loop())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start voice engine: {e}")
            return False
    
    def stop_listening(self):
        """Stop the voice recognition system"""
        self.is_listening = False
        self.speech_recognizer.stop()
        self.logger.info("Voice engine stopped listening")
    
    async def _main_processing_loop(self):
        """Main async loop for processing voice commands"""
        while self.is_listening:
            try:
                # Capture audio input
                audio_data = await self.speech_recognizer.capture_audio()
                
                if audio_data and not self.is_processing:
                    # Process the audio in the background
                    asyncio.create_task(self._process_audio_async(audio_data))
                
                # Small delay to prevent excessive CPU usage
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in main processing loop: {e}")
                await asyncio.sleep(1)  # Wait before retrying
    
    async def _process_audio_async(self, audio_data):
        """Process audio data asynchronously"""
        start_time = time.time()
        
        try:
            self.is_processing = True
            
            # Convert speech to text
            text = await self.speech_recognizer.transcribe_audio(audio_data)
            
            if text:
                self.logger.info(f"Transcribed text: '{text}'")
                
                # Process the command
                result = await self.process_text_command(text)
                
                # Update metrics
                processing_time = time.time() - start_time
                self._update_metrics(result["success"], processing_time)
                
                # Add to command history
                self._add_to_history(text, result, processing_time)
                
                # Notify callbacks
                await self._notify_callbacks(result)
            
        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
            result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await self._notify_callbacks(result)
        
        finally:
            self.is_processing = False
    
    async def process_text_command(self, text: str) -> Dict:
        """Process a text command through the NLP and automation pipeline"""
        try:
            self.logger.info(f"Processing command: '{text}'")
            
            # Step 1: NLP Processing - Extract intent and entities
            nlp_result = await self.nlp_processor.analyze_command(
                text, self.current_context
            )
            
            if not nlp_result["success"]:
                return {
                    "success": False,
                    "error": "Failed to understand command",
                    "original_text": text,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Step 2: Execute the command
            execution_result = await self.automation_engine.execute_command(
                nlp_result["intent"], 
                nlp_result["entities"],
                nlp_result["parameters"]
            )
            
            # Step 3: Update context for future commands
            self._update_context(nlp_result, execution_result)
            
            # Step 4: Prepare response
            response = {
                "success": execution_result["success"],
                "original_text": text,
                "intent": nlp_result["intent"],
                "entities": nlp_result["entities"],
                "action_taken": execution_result.get("description", ""),
                "timestamp": datetime.now().isoformat()
            }
            
            if not execution_result["success"]:
                response["error"] = execution_result.get("error", "Unknown error")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing text command: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_text": text,
                "timestamp": datetime.now().isoformat()
            }
    
    async def process_next_command(self) -> Optional[Dict]:
        """Process the next command from the queue (used by UI thread)"""
        try:
            # Non-blocking queue check
            if not self.command_queue.empty():
                command_data = await asyncio.wait_for(
                    self.command_queue.get(), timeout=0.1
                )
                result = await self.process_text_command(command_data["text"])
                return result
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            self.logger.error(f"Error processing queued command: {e}")
        
        return None
    
    async def queue_text_command(self, text: str):
        """Add a text command to processing queue"""
        await self.command_queue.put({
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
    
    def _update_context(self, nlp_result: Dict, execution_result: Dict):
        """Update conversation context based on command results"""
        self.current_context.update({
            "last_intent": nlp_result["intent"],
            "last_entities": nlp_result["entities"],
            "last_success": execution_result["success"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep context history limited
        if len(self.current_context) > 10:
            # Remove oldest entries
            items = list(self.current_context.items())
            self.current_context = dict(items[-10:])
    
    def _add_to_history(self, text: str, result: Dict, processing_time: float):
        """Add command to history"""
        history_entry = {
            "id": len(self.command_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "intent": result.get("intent", "unknown"),
            "success": result["success"],
            "processing_time": processing_time,
            "description": result.get("action_taken", "")
        }
        
        if not result["success"]:
            history_entry["error"] = result.get("error", "Unknown error")
        
        self.command_history.append(history_entry)
        
        # Keep history limited to last 100 commands
        if len(self.command_history) > 100:
            self.command_history.pop(0)
    
    def _update_metrics(self, success: bool, processing_time: float):
        """Update performance metrics"""
        self.metrics["commands_processed"] += 1
        
        if success:
            self.metrics["successful_commands"] += 1
        else:
            self.metrics["failed_commands"] += 1
        
        # Update average response time
        total_commands = self.metrics["commands_processed"]
        current_avg = self.metrics["average_response_time"]
        self.metrics["average_response_time"] = (
            (current_avg * (total_commands - 1) + processing_time) / total_commands
        )
    
    async def _notify_callbacks(self, result: Dict):
        """Notify registered callbacks about command results"""
        for callback in self.response_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                self.logger.error(f"Error in callback: {e}")
    
    def add_response_callback(self, callback):
        """Add a callback for command processing results"""
        self.response_callbacks.append(callback)
    
    def remove_response_callback(self, callback):
        """Remove a callback"""
        if callback in self.response_callbacks:
            self.response_callbacks.remove(callback)
    
    def get_metrics(self) -> Dict:
        """Get current performance metrics"""
        current_time = datetime.now()
        session_duration = (current_time - self.metrics["session_start"]).total_seconds()
        
        return {
            **self.metrics,
            "session_duration_seconds": session_duration,
            "commands_per_minute": (
                self.metrics["commands_processed"] / (session_duration / 60)
                if session_duration > 0 else 0
            ),
            "success_rate": (
                self.metrics["successful_commands"] / self.metrics["commands_processed"]
                if self.metrics["commands_processed"] > 0 else 0
            )
        }
    
    def get_command_history(self, limit: int = 50) -> List[Dict]:
        """Get recent command history"""
        return self.command_history[-limit:] if self.command_history else []
    
    def clear_history(self):
        """Clear command history"""
        self.command_history.clear()
        self.logger.info("Command history cleared")
    
    def get_current_context(self) -> Dict:
        """Get current conversation context"""
        return self.current_context.copy()
    
    def set_language(self, language: str):
        """Set the processing language"""
        self.config.set("language", language)
        self.speech_recognizer.set_language(language)
        self.nlp_processor.set_language(language)
        self.logger.info(f"Language set to: {language}")
    
    def set_offline_mode(self, offline: bool):
        """Enable/disable offline processing mode"""
        self.config.set("offline_mode", offline)
        self.speech_recognizer.set_offline_mode(offline)
        self.nlp_processor.set_offline_mode(offline)
        self.logger.info(f"Offline mode: {'enabled' if offline else 'disabled'}")
    
    def cleanup(self):
        """Cleanup resources before shutdown"""
        self.logger.info("Cleaning up voice engine resources...")
        
        self.stop_listening()
        
        if hasattr(self.speech_recognizer, 'cleanup'):
            self.speech_recognizer.cleanup()
        
        if hasattr(self.automation_engine, 'cleanup'):
            self.automation_engine.cleanup()
        
        self.logger.info("Voice engine cleanup completed")
    
    def export_session_data(self) -> Dict:
        """Export session data for analysis"""
        return {
            "session_id": self.session_id,
            "metrics": self.get_metrics(),
            "command_history": self.get_command_history(),
            "context": self.get_current_context(),
            "config": self.config.get_all()
        }