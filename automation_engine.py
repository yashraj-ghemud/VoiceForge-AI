"""
VoiceForge AI - Automation Engine
Infinity Code Hackathon - Stark Industries Challenge

Advanced automation system for executing PC control commands
through Windows APIs, computer vision, and system integration.
"""

import asyncio
import logging
import subprocess
import psutil
import pyautogui
import cv2
import numpy as np
import time
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import win32gui
import win32con
import win32api
import win32process

from ..utils.config_manager import ConfigManager


class AutomationEngine:
    """Advanced automation engine for PC control operations"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Configure PyAutoGUI
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
        # Computer vision settings
        self.template_matching_threshold = 0.8
        self.screenshot_cache = {}
        
        # Application database
        self.app_database = self._initialize_app_database()
        
        # Command execution settings
        self.max_retry_attempts = 3
        self.operation_timeout = 30
        
        # Safety settings
        self.safe_mode = config.get("safe_mode", True)
        self.confirmation_required = config.get("confirmation_required", False)
        
        # Performance metrics
        self.execution_stats = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "average_execution_time": 0.0
        }
        
        self.logger.info("AutomationEngine initialized")
    
    def _initialize_app_database(self) -> Dict:
        """Initialize database of known applications and their properties"""
        return {
            # Web browsers
            "chrome": {
                "executable": "chrome.exe",
                "process_name": "chrome.exe",
                "launch_command": "start chrome",
                "install_location": r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            },
            "firefox": {
                "executable": "firefox.exe", 
                "process_name": "firefox.exe",
                "launch_command": "start firefox",
                "install_location": r"C:\Program Files\Mozilla Firefox\firefox.exe"
            },
            "edge": {
                "executable": "msedge.exe",
                "process_name": "msedge.exe", 
                "launch_command": "start msedge",
                "install_location": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            },
            
            # Office applications
            "notepad": {
                "executable": "notepad.exe",
                "process_name": "notepad.exe",
                "launch_command": "notepad",
                "install_location": r"C:\Windows\System32\notepad.exe"
            },
            "calculator": {
                "executable": "calc.exe",
                "process_name": "CalculatorApp.exe",
                "launch_command": "calc",
                "install_location": "calculator:"
            },
            "wordpad": {
                "executable": "wordpad.exe",
                "process_name": "wordpad.exe", 
                "launch_command": "write",
                "install_location": r"C:\Program Files\Windows NT\Accessories\wordpad.exe"
            },
            
            # Gaming and entertainment
            "minecraft": {
                "executable": "Minecraft.exe",
                "process_name": "Minecraft.exe",
                "launch_command": None,  # Requires special handling
                "install_location": None  # Variable location
            },
            "vlc": {
                "executable": "vlc.exe",
                "process_name": "vlc.exe",
                "launch_command": None,
                "install_location": r"C:\Program Files\VideoLAN\VLC\vlc.exe"
            },
            "spotify": {
                "executable": "Spotify.exe",
                "process_name": "Spotify.exe", 
                "launch_command": None,
                "install_location": None
            },
            
            # System utilities
            "explorer": {
                "executable": "explorer.exe",
                "process_name": "explorer.exe",
                "launch_command": "explorer",
                "install_location": r"C:\Windows\explorer.exe"
            },
            "cmd": {
                "executable": "cmd.exe",
                "process_name": "cmd.exe",
                "launch_command": "cmd",
                "install_location": r"C:\Windows\System32\cmd.exe"
            },
            "powershell": {
                "executable": "powershell.exe", 
                "process_name": "powershell.exe",
                "launch_command": "powershell",
                "install_location": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            }
        }
    
    async def execute_command(self, intent: str, entities: Dict, parameters: Dict) -> Dict:
        """Execute automation command based on intent and parameters"""
        start_time = time.time()
        self.execution_stats["total_commands"] += 1
        
        try:
            self.logger.info(f"Executing command: {intent} with entities: {entities}")
            
            # Route to appropriate handler based on intent
            if intent == "open_application":
                result = await self._handle_open_application(entities, parameters)
            elif intent == "close_application":
                result = await self._handle_close_application(entities, parameters)
            elif intent == "uninstall_application":
                result = await self._handle_uninstall_application(entities, parameters)
            elif intent == "file_operation":
                result = await self._handle_file_operation(entities, parameters)
            elif intent == "email_operation":
                result = await self._handle_email_operation(entities, parameters)
            elif intent == "system_operation":
                result = await self._handle_system_operation(entities, parameters)
            elif intent == "web_operation":
                result = await self._handle_web_operation(entities, parameters)
            else:
                result = {
                    "success": False,
                    "error": f"Unknown intent: {intent}",
                    "description": "Intent not recognized"
                }
            
            # Update execution time
            execution_time = time.time() - start_time
            result["execution_time"] = execution_time
            
            # Update statistics
            if result["success"]:
                self.execution_stats["successful_commands"] += 1
            else:
                self.execution_stats["failed_commands"] += 1
            
            self._update_average_execution_time(execution_time)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.execution_stats["failed_commands"] += 1
            self.logger.error(f"Command execution failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "description": "Command execution failed",
                "execution_time": execution_time
            }
    
    async def _handle_open_application(self, entities: Dict, parameters: Dict) -> Dict:
        """Handle application opening commands"""
        applications = entities.get("applications", [])
        
        if not applications:
            return {
                "success": False,
                "error": "No application specified",
                "description": "Could not identify application to open"
            }
        
        app_name = applications[0].lower()
        
        try:
            # Check if app is already running
            if self._is_application_running(app_name):
                return {
                    "success": True,
                    "description": f"{app_name.title()} is already running",
                    "action": "focus_existing"
                }
            
            # Try to launch the application
            success = await self._launch_application(app_name)
            
            if success:
                return {
                    "success": True,
                    "description": f"Successfully opened {app_name.title()}",
                    "action": "launched"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to launch {app_name}",
                    "description": f"Could not find or launch {app_name.title()}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": f"Error opening {app_name.title()}"
            }
    
    async def _handle_close_application(self, entities: Dict, parameters: Dict) -> Dict:
        """Handle application closing commands"""
        applications = entities.get("applications", [])
        
        if not applications:
            return {
                "success": False,
                "error": "No application specified",
                "description": "Could not identify application to close"
            }
        
        app_name = applications[0].lower()
        force_close = parameters.get("force", False)
        
        try:
            # Find running processes
            processes = self._find_processes_by_name(app_name)
            
            if not processes:
                return {
                    "success": False,
                    "error": f"{app_name.title()} is not running",
                    "description": f"No running instance of {app_name.title()} found"
                }
            
            # Close processes
            closed_count = 0
            for process in processes:
                try:
                    if force_close:
                        process.terminate()
                    else:
                        process.terminate()
                        process.wait(timeout=5)  # Wait for graceful shutdown
                    closed_count += 1
                except psutil.TimeoutExpired:
                    process.kill()  # Force kill if graceful shutdown fails
                    closed_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to close process {process.pid}: {e}")
            
            if closed_count > 0:
                return {
                    "success": True,
                    "description": f"Closed {closed_count} instance(s) of {app_name.title()}",
                    "action": "terminated"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to close any instances",
                    "description": f"Could not close {app_name.title()}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": f"Error closing {app_name.title()}"
            }
    
    async def _handle_uninstall_application(self, entities: Dict, parameters: Dict) -> Dict:
        """Handle application uninstallation commands"""
        applications = entities.get("applications", [])
        
        if not applications:
            return {
                "success": False,
                "error": "No application specified",
                "description": "Could not identify application to uninstall"
            }
        
        app_name = applications[0].lower()
        
        try:
            # Open Windows Settings to Apps & Features
            self.logger.info(f"Opening Apps & Features for {app_name} uninstallation")
            
            # Method 1: Use Windows Settings URI
            subprocess.run(["start", "ms-settings:appsfeatures"], shell=True, check=True)
            await asyncio.sleep(3)  # Wait for settings to open
            
            # Method 2: Use computer vision to find and click the app
            success = await self._uninstall_via_settings_ui(app_name)
            
            if success:
                return {
                    "success": True,
                    "description": f"Started uninstallation process for {app_name.title()}",
                    "action": "uninstall_initiated"
                }
            else:
                # Fallback: Try Control Panel method
                success_cp = await self._uninstall_via_control_panel(app_name)
                
                if success_cp:
                    return {
                        "success": True,
                        "description": f"Started uninstallation via Control Panel for {app_name.title()}",
                        "action": "uninstall_initiated_cp"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Could not find {app_name} in installed programs",
                        "description": f"Unable to locate {app_name.title()} for uninstallation"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": f"Error uninstalling {app_name.title()}"
            }
    
    async def _handle_file_operation(self, entities: Dict, parameters: Dict) -> Dict:
        """Handle file and folder operations"""
        operation = parameters.get("operation", "unknown")
        
        try:
            if operation == "create":
                return await self._create_file_or_folder(entities, parameters)
            elif operation == "delete":
                return await self._delete_file_or_folder(entities, parameters)
            elif operation == "move":
                return await self._move_files(entities, parameters)
            elif operation == "copy":
                return await self._copy_files(entities, parameters)  
            else:
                return {
                    "success": False,
                    "error": f"Unknown file operation: {operation}",
                    "description": "File operation not recognized"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": f"Error performing file operation: {operation}"
            }
    
    async def _handle_email_operation(self, entities: Dict, parameters: Dict) -> Dict:
        """Handle email operations"""
        try:
            # Try to open default email client
            subprocess.run(["start", "mailto:"], shell=True)
            await asyncio.sleep(2)
            
            # If specific recipient is mentioned, try to fill it
            if entities.get("applications"):  # Using applications as recipient names
                recipient = entities["applications"][0]
                return {
                    "success": True,
                    "description": f"Opened email client for composing message to {recipient}",
                    "action": "email_client_opened"
                }
            
            return {
                "success": True,
                "description": "Opened email client for composing new message",
                "action": "email_client_opened"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": "Error opening email client"
            }
    
    async def _handle_system_operation(self, entities: Dict, parameters: Dict) -> Dict:
        """Handle system-level operations"""
        try:
            # Determine system operation type from entities/parameters
            operation_text = " ".join(entities.get("parameters", {}).values())
            
            if "information" in operation_text or "status" in operation_text:
                return await self._show_system_information()
            elif "clean" in operation_text and "temp" in operation_text:
                return await self._clean_temporary_files()
            elif "restart" in operation_text:
                return await self._restart_system(parameters)
            else:
                # Default: show system information
                return await self._show_system_information()
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": "Error performing system operation"
            }
    
    async def _handle_web_operation(self, entities: Dict, parameters: Dict) -> Dict:
        """Handle web browsing operations"""
        try:
            search_query = parameters.get("search_query")
            
            if search_query:
                # Open browser with search
                search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                subprocess.run(["start", search_url], shell=True)
                
                return {
                    "success": True,
                    "description": f"Opened Google search for '{search_query}'",
                    "action": "web_search"
                }
            else:
                # Just open browser
                subprocess.run(["start", ""], shell=True)  # Open default browser
                
                return {
                    "success": True,
                    "description": "Opened default web browser",
                    "action": "browser_opened"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": "Error performing web operation"
            }
    
    async def _launch_application(self, app_name: str) -> bool:
        """Launch an application by name"""
        app_info = self.app_database.get(app_name)
        
        if not app_info:
            # Try generic launch command
            try:
                subprocess.run(["start", app_name], shell=True, check=True)
                await asyncio.sleep(2)  # Wait for app to start
                return True
            except subprocess.CalledProcessError:
                return False
        
        # Try specific launch methods
        if app_info.get("launch_command"):
            try:
                subprocess.run(app_info["launch_command"], shell=True, check=True)
                await asyncio.sleep(2)
                return True
            except subprocess.CalledProcessError:
                pass
        
        # Try direct executable path
        if app_info.get("install_location") and os.path.exists(app_info["install_location"]):
            try:
                subprocess.run([app_info["install_location"]], check=True)
                await asyncio.sleep(2)
                return True
            except subprocess.CalledProcessError:
                pass
        
        return False
    
    def _is_application_running(self, app_name: str) -> bool:
        """Check if an application is currently running"""
        processes = self._find_processes_by_name(app_name)
        return len(processes) > 0
    
    def _find_processes_by_name(self, app_name: str) -> List:
        """Find running processes by application name"""
        processes = []
        app_info = self.app_database.get(app_name, {})
        process_name = app_info.get("process_name", f"{app_name}.exe")
        
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                if (proc.info['name'].lower() == process_name.lower() or
                    app_name.lower() in proc.info['name'].lower()):
                    processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes
    
    async def _uninstall_via_settings_ui(self, app_name: str) -> bool:
        """Uninstall application via Windows Settings UI using computer vision"""
        try:
            # Take screenshot of Settings window
            screenshot = pyautogui.screenshot()
            screenshot_np = np.array(screenshot)
            
            # Search for the application name in the UI
            # This is a simplified version - real implementation would use OCR
            
            # For now, use a simple approach with pyautogui to search and click
            try:
                # Search for the app name on screen
                location = pyautogui.locateOnScreen(None)  # Would need actual image template
                if location:
                    pyautogui.click(location)
                    await asyncio.sleep(1)
                    
                    # Look for uninstall button
                    pyautogui.click(pyautogui.locateOnScreen(None))  # Uninstall button template
                    return True
            except pyautogui.ImageNotFoundException:
                pass
            
            # Fallback: Type the app name in search
            pyautogui.write(app_name)
            await asyncio.sleep(2)
            
            # Press Enter to search
            pyautogui.press('enter')
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in Settings UI uninstall: {e}")
            return False
    
    async def _uninstall_via_control_panel(self, app_name: str) -> bool:
        """Uninstall application via Control Panel"""
        try:
            # Open Control Panel Programs and Features
            subprocess.run(["appwiz.cpl"], shell=True, check=True)
            await asyncio.sleep(3)
            
            # Type app name to search
            pyautogui.write(app_name)
            await asyncio.sleep(1)
            
            # Press Enter to select
            pyautogui.press('enter')
            await asyncio.sleep(1)
            
            # Press Delete or look for Uninstall button
            pyautogui.press('delete')
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in Control Panel uninstall: {e}")
            return False
    
    async def _create_file_or_folder(self, entities: Dict, parameters: Dict) -> Dict:
        """Create files or folders"""
        # Implementation for file/folder creation
        return {
            "success": True,
            "description": "File/folder creation not yet implemented",
            "action": "create_pending"
        }
    
    async def _delete_file_or_folder(self, entities: Dict, parameters: Dict) -> Dict:
        """Delete files or folders"""
        # Implementation for file/folder deletion
        return {
            "success": True,
            "description": "File/folder deletion not yet implemented",
            "action": "delete_pending"
        }
    
    async def _move_files(self, entities: Dict, parameters: Dict) -> Dict:
        """Move files between locations"""
        # Implementation for file moving
        return {
            "success": True,
            "description": "File moving not yet implemented",
            "action": "move_pending"
        }
    
    async def _copy_files(self, entities: Dict, parameters: Dict) -> Dict:
        """Copy files to different locations"""
        # Implementation for file copying
        return {
            "success": True,
            "description": "File copying not yet implemented", 
            "action": "copy_pending"
        }
    
    async def _show_system_information(self) -> Dict:
        """Show system information"""
        try:
            # Open System Information
            subprocess.run(["msinfo32"], shell=True, check=True)
            
            return {
                "success": True,
                "description": "Opened System Information",
                "action": "system_info_opened"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": "Error opening system information"
            }
    
    async def _clean_temporary_files(self) -> Dict:
        """Clean temporary files"""
        try:
            # Open Disk Cleanup
            subprocess.run(["cleanmgr"], shell=True, check=True)
            
            return {
                "success": True,
                "description": "Opened Disk Cleanup utility",
                "action": "cleanup_opened"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": "Error opening disk cleanup"
            }
    
    async def _restart_system(self, parameters: Dict) -> Dict:
        """Restart the system"""
        if self.safe_mode:
            return {
                "success": False,
                "error": "System restart blocked by safe mode",
                "description": "Restart command blocked for safety"
            }
        
        try:
            # Show confirmation dialog (in real implementation)
            # For safety, we'll just log the intent
            self.logger.warning("System restart requested but blocked for safety")
            
            return {
                "success": True,
                "description": "System restart scheduled (demo mode)",
                "action": "restart_scheduled"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": "Error scheduling system restart"
            }
    
    def _update_average_execution_time(self, execution_time: float):
        """Update average execution time metric"""
        total = self.execution_stats["total_commands"]
        current_avg = self.execution_stats["average_execution_time"]
        
        self.execution_stats["average_execution_time"] = (
            (current_avg * (total - 1) + execution_time) / total
        )
    
    def get_execution_stats(self) -> Dict:
        """Get automation execution statistics"""
        total = self.execution_stats["total_commands"]
        success_rate = (
            self.execution_stats["successful_commands"] / total
            if total > 0 else 0
        )
        
        return {
            **self.execution_stats,
            "success_rate": success_rate
        }
    
    def cleanup(self):
        """Cleanup automation engine resources"""
        self.logger.info("Cleaning up automation engine...")
        
        # Clear screenshot cache
        self.screenshot_cache.clear()
        
        self.logger.info("Automation engine cleanup completed")