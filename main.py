#!/usr/bin/env python3
"""
VoiceForge AI - Main Application Entry Point
Infinity Code Hackathon - Stark Industries Challenge

This is the main entry point for the VoiceForge AI application.
It initializes the voice engine, UI components, and starts the application.
"""

import sys
import asyncio
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QIcon

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.voice_engine import VoiceEngine
from src.ui.main_window import MainWindow
from src.utils.config_manager import ConfigManager
from src.utils.logger import setup_logger

class VoiceEngineThread(QThread):
    """Thread for running the voice engine asynchronously"""
    command_processed = pyqtSignal(dict)
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, voice_engine):
        super().__init__()
        self.voice_engine = voice_engine
        self.running = False
    
    def run(self):
        """Run the voice engine in a separate thread"""
        self.running = True
        self.status_updated.emit("Voice engine started")
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._async_main())
        except Exception as e:
            self.error_occurred.emit(f"Voice engine error: {str(e)}")
        finally:
            loop.close()
    
    async def _async_main(self):
        """Async main loop for voice processing"""
        while self.running:
            try:
                result = await self.voice_engine.process_next_command()
                if result:
                    self.command_processed.emit(result)
                await asyncio.sleep(0.1)  # Prevent busy waiting
            except Exception as e:
                self.error_occurred.emit(f"Command processing error: {str(e)}")
                await asyncio.sleep(1)  # Wait before retrying
    
    def stop(self):
        """Stop the voice engine thread"""
        self.running = False
        self.voice_engine.stop_listening()

class VoiceForgeApplication:
    """Main application class"""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.voice_engine = None
        self.voice_thread = None
        self.config = None
        self.logger = None
    
    def initialize(self):
        """Initialize all application components"""
        # Setup logging
        self.logger = setup_logger()
        self.logger.info("Initializing VoiceForge AI application...")
        
        # Initialize configuration
        self.config = ConfigManager()
        
        # Create Qt application
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("VoiceForge AI")
        self.app.setApplicationVersion("1.0.0")
        self.app.setOrganizationName("VoiceForge Technologies")
        
        # Set application icon
        icon_path = project_root / "assets" / "icons" / "voiceforge_icon.png"
        if icon_path.exists():
            self.app.setWindowIcon(QIcon(str(icon_path)))
        
        # Initialize voice engine
        try:
            self.voice_engine = VoiceEngine(self.config)
            self.logger.info("Voice engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize voice engine: {e}")
            self._show_error("Voice Engine Error", 
                           f"Failed to initialize voice engine: {e}")
            return False
        
        # Create main window
        self.main_window = MainWindow(self.voice_engine, self.config)
        
        # Setup voice engine thread
        self.voice_thread = VoiceEngineThread(self.voice_engine)
        self.voice_thread.command_processed.connect(
            self.main_window.on_command_processed
        )
        self.voice_thread.status_updated.connect(
            self.main_window.update_status
        )
        self.voice_thread.error_occurred.connect(
            self.main_window.show_error
        )
        
        return True
    
    def run(self):
        """Run the application"""
        if not self.initialize():
            return 1
        
        try:
            # Show main window
            self.main_window.show()
            self.logger.info("VoiceForge AI application started")
            
            # Start voice engine thread
            self.voice_thread.start()
            
            # Run Qt event loop
            exit_code = self.app.exec()
            
            # Cleanup
            self.cleanup()
            
            return exit_code
            
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            self._show_error("Application Error", f"An error occurred: {e}")
            return 1
    
    def cleanup(self):
        """Cleanup application resources"""
        self.logger.info("Cleaning up application resources...")
        
        if self.voice_thread and self.voice_thread.isRunning():
            self.voice_thread.stop()
            self.voice_thread.wait(3000)  # Wait up to 3 seconds
            if self.voice_thread.isRunning():
                self.voice_thread.terminate()
        
        if self.voice_engine:
            self.voice_engine.cleanup()
        
        self.logger.info("Application cleanup completed")
    
    def _show_error(self, title, message):
        """Show error message to user"""
        if self.app:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.exec()

def main():
    """Main entry point"""
    try:
        app = VoiceForgeApplication()
        return app.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 0
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)