"""
VoiceForge AI - Natural Language Processing Module
Infinity Code Hackathon - Stark Industries Challenge

Advanced NLP system for intent recognition, entity extraction,
and context-aware command processing in Hindi and English.
"""

import asyncio
import logging
import re
import json
import openai
import spacy
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import pickle
import os

from ..utils.config_manager import ConfigManager


class NLPProcessor:
    """Advanced NLP processor for bilingual command understanding"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize OpenAI client
        self.openai_client = None
        if config.get("openai_api_key"):
            openai.api_key = config.get("openai_api_key")
            self.openai_client = openai
        
        # Language settings
        self.primary_language = config.get("language", "en")
        self.offline_mode = config.get("offline_mode", False)
        
        # Load spaCy models
        self.nlp_en = None
        self.nlp_hi = None
        self._load_spacy_models()
        
        # Intent patterns for rule-based processing
        self.intent_patterns = self._initialize_intent_patterns()
        
        # Entity patterns
        self.entity_patterns = self._initialize_entity_patterns()
        
        # Context management
        self.context_window = 5  # Remember last 5 interactions
        self.conversation_context = []
        
        # Custom trained model (if available)
        self.custom_model = None
        self._load_custom_model()
        
        # Performance metrics
        self.processing_stats = {
            "total_processed": 0,
            "successful_extractions": 0,
            "fallback_used": 0,
            "average_confidence": 0.0
        }
        
        self.logger.info("NLPProcessor initialized")
    
    def _load_spacy_models(self):
        """Load spaCy models for multilingual processing"""
        try:
            # Load English model
            self.nlp_en = spacy.load("en_core_web_sm")
            self.logger.info("English spaCy model loaded")
        except OSError:
            self.logger.warning("English spaCy model not found. Install with: python -m spacy download en_core_web_sm")
        
        try:
            # Load Hindi model (if available)
            self.nlp_hi = spacy.load("hi_core_news_sm")
            self.logger.info("Hindi spaCy model loaded")
        except OSError:
            self.logger.warning("Hindi spaCy model not available")
    
    def _initialize_intent_patterns(self) -> Dict[str, List[str]]:
        """Initialize regex patterns for intent recognition"""
        return {
            "open_application": [
                r"(?:open|launch|start|run)\s+(\w+)",
                r"(\w+)\s+(?:kholo|chalu\s+karo|start\s+karo)",
                r"launch\s+the\s+(\w+)",
                r"(\w+)\s+application\s+(?:open|start)",
                r"show\s+me\s+(\w+)"
            ],
            "close_application": [
                r"(?:close|quit|exit|stop)\s+(\w+)",
                r"(\w+)\s+(?:band\s+karo|close\s+karo|exit\s+karo)",
                r"shut\s+down\s+(\w+)",
                r"terminate\s+(\w+)",
                r"kill\s+(\w+)\s+process"
            ],
            "uninstall_application": [
                r"(?:uninstall|remove|delete)\s+(\w+)",
                r"(\w+)\s+(?:ko\s+)?(?:delete|uninstall|remove)\s+kar.*",
                r"get\s+rid\s+of\s+(\w+)",
                r"(\w+)\s+hatao",
                r"(\w+)\s+software\s+remove\s+karo"
            ],
            "file_operation": [
                r"(?:create|make|new)\s+(?:folder|directory)\s+(?:called\s+)?['\"]?([^'\"]+)['\"]?",
                r"folder\s+banao\s+['\"]?([^'\"]+)['\"]?",
                r"(?:delete|remove)\s+(?:file|folder)\s+['\"]?([^'\"]+)['\"]?",
                r"['\"]?([^'\"]+)['\"]?\s+(?:file|folder)\s+delete\s+karo",
                r"move\s+(?:all\s+)?(\w+)\s+files?\s+(?:from\s+)?([^\\s]+)?\s+(?:to\s+)?([^\\s]+)?",
                r"copy\s+['\"]?([^'\"]+)['\"]?\s+to\s+['\"]?([^'\"]+)['\"]?"
            ],
            "email_operation": [
                r"send\s+email\s+to\s+(\w+)(?:\s+with\s+(.+))?",
                r"(\w+)\s+ko\s+email\s+bhejo(?:\s+(.+)\s+ke\s+saath)?",
                r"compose\s+email\s+for\s+(\w+)",
                r"email\s+draft\s+karo\s+(\w+)\s+ke\s+liye"
            ],
            "system_operation": [
                r"(?:check|show)\s+system\s+(?:information|performance|status)",
                r"system\s+(?:ki\s+)?(?:information|performance|status)\s+(?:dikhao|batao)",
                r"clean\s+(?:up\s+)?(?:temporary|temp)\s+files",
                r"(?:temporary|temp)\s+files\s+(?:clean|delete)\s+karo",
                r"restart\s+(?:the\s+)?(?:computer|system|pc)",
                r"(?:computer|system|pc)\s+restart\s+karo"
            ],
            "web_operation": [
                r"(?:open|visit|go\s+to)\s+(?:website\s+)?([\\w\\.-]+\\.\\w+)",
                r"([\\w\\.-]+\\.\\w+)\s+(?:website\s+)?(?:kholo|open\s+karo)",
                r"search\s+(?:for\s+)?['\"]?([^'\"]+)['\"]?\s+(?:on\s+)?(?:google|web)?",
                r"google\s+(?:mein\s+|pe\s+)?['\"]?([^'\"]+)['\"]?\s+search\s+karo"
            ]
        }
    
    def _initialize_entity_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for entity extraction"""
        return {
            "application_names": [
                r"\\b(chrome|firefox|edge|safari|browser)\\b",
                r"\\b(notepad|wordpad|word|excel|powerpoint)\\b",
                r"\\b(calculator|calc|photoshop|vlc|spotify)\\b",
                r"\\b(minecraft|steam|discord|zoom|teams)\\b",
                r"\\b(explorer|file\\s+manager|control\\s+panel)\\b"
            ],
            "file_types": [
                r"\\b(pdf|doc|docx|txt|jpg|png|gif|mp4|mp3)\\b",
                r"\\b(excel|powerpoint|image|video|audio|document)\\b"
            ],
            "email_addresses": [
                r"\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b"
            ],
            "file_paths": [
                r"[A-Za-z]:\\\\[^\\s]+",
                r"~/[^\\s]+",
                r"\\./[^\\s]+"
            ]
        }
    
    def _load_custom_model(self):
        """Load custom trained model if available"""
        model_path = self.config.get("custom_model_path", "assets/models/custom_nlp_model.pkl")
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    self.custom_model = pickle.load(f)
                self.logger.info("Custom NLP model loaded")
            except Exception as e:
                self.logger.warning(f"Failed to load custom model: {e}")
    
    async def analyze_command(self, text: str, context: Dict = None) -> Dict:
        """Analyze command text and extract intent, entities, and parameters"""
        self.processing_stats["total_processed"] += 1
        
        try:
            # Preprocess text
            processed_text = self._preprocess_text(text)
            
            # Detect language
            language = self._detect_language(processed_text)
            
            # Extract intent using multiple methods
            intent_result = await self._extract_intent(processed_text, language, context)
            
            # Extract entities
            entities = self._extract_entities(processed_text, language)
            
            # Extract parameters
            parameters = self._extract_parameters(processed_text, intent_result["intent"], entities)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(intent_result, entities)
            
            # Update context
            self._update_conversation_context(text, intent_result["intent"], entities)
            
            result = {
                "success": True,
                "original_text": text,
                "processed_text": processed_text,
                "language": language,
                "intent": intent_result["intent"],
                "entities": entities,
                "parameters": parameters,
                "confidence": confidence,
                "method_used": intent_result["method"],
                "timestamp": datetime.now().isoformat()
            }
            
            self.processing_stats["successful_extractions"] += 1
            self.logger.info(f"NLP Analysis: {intent_result['intent']} (confidence: {confidence:.2f})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"NLP processing error: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_text": text,
                "timestamp": datetime.now().isoformat()
            }
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess input text for better analysis"""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove extra whitespace
        text = re.sub(r'\\s+', ' ', text)
        
        # Handle common contractions
        contractions = {
            "can't": "cannot",
            "won't": "will not",
            "n't": " not",
            "'ll": " will",
            "'ve": " have",
            "'re": " are",
            "'m": " am"
        }
        
        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)
        
        # Handle Hindi romanization variations
        hindi_variations = {
            "karo": "karo",
            "kro": "karo",
            "kar do": "karo",
            "kholo": "kholo",
            "khole": "kholo",
            "band": "band",
            "bandh": "band"
        }
        
        for variation, standard in hindi_variations.items():
            text = re.sub(r'\\b' + variation + r'\\b', standard, text)
        
        return text
    
    def _detect_language(self, text: str) -> str:
        """Detect the primary language of the text"""
        # Simple heuristic-based language detection
        hindi_words = [
            "karo", "kholo", "band", "dekho", "batao", "dikhao",
            "bhejo", "banao", "hatao", "chalao", "roko", "ko", "ka", "ki",
            "mein", "pe", "se", "tak", "aur", "ya"
        ]
        
        english_words = [
            "open", "close", "start", "stop", "show", "create", "delete",
            "send", "make", "run", "launch", "quit", "exit", "the", "and",
            "or", "to", "from", "with", "in", "on", "at"
        ]
        
        hindi_count = sum(1 for word in hindi_words if word in text.lower())
        english_count = sum(1 for word in english_words if word in text.lower())
        
        if hindi_count > english_count:
            return "hi"
        elif english_count > 0:
            return "en"
        else:
            # Default to primary language setting
            return self.primary_language
    
    async def _extract_intent(self, text: str, language: str, context: Dict = None) -> Dict:
        """Extract intent using multiple methods"""
        # Method 1: Try custom model first
        if self.custom_model:
            try:
                intent = self.custom_model.predict([text])[0]
                return {"intent": intent, "method": "custom_model", "confidence": 0.9}
            except Exception as e:
                self.logger.debug(f"Custom model failed: {e}")
        
        # Method 2: Try OpenAI GPT if available and not in offline mode
        if not self.offline_mode and self.openai_client:
            try:
                gpt_result = await self._extract_intent_with_gpt(text, context)
                if gpt_result["confidence"] > 0.7:
                    return gpt_result
            except Exception as e:
                self.logger.debug(f"GPT intent extraction failed: {e}")
        
        # Method 3: Rule-based pattern matching (fallback)
        pattern_result = self._extract_intent_with_patterns(text)
        self.processing_stats["fallback_used"] += 1
        return pattern_result
    
    async def _extract_intent_with_gpt(self, text: str, context: Dict = None) -> Dict:
        """Extract intent using OpenAI GPT"""
        context_info = ""
        if context and self.conversation_context:
            recent_context = self.conversation_context[-3:]  # Last 3 interactions
            context_info = f"\\nRecent context: {json.dumps(recent_context)}"
        
        prompt = f"""
        Analyze this voice command and classify the intent. Consider both Hindi and English text.
        
        Text: "{text}"{context_info}
        
        Available intents:
        - open_application: Opening/launching software or apps
        - close_application: Closing/quitting running applications  
        - uninstall_application: Removing/uninstalling software
        - file_operation: Creating, deleting, moving, copying files/folders
        - email_operation: Sending, composing, managing emails
        - system_operation: System maintenance, information, restart
        - web_operation: Opening websites, web searches
        - unknown: Cannot determine intent
        
        Respond with JSON format:
        {{
            "intent": "intent_name",
            "confidence": 0.95,
            "reasoning": "brief explanation"
        }}
        """
        
        try:
            response = await self.openai_client.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            return {
                "intent": result["intent"],
                "method": "gpt",
                "confidence": result.get("confidence", 0.8),
                "reasoning": result.get("reasoning", "")
            }
            
        except Exception as e:
            self.logger.error(f"GPT intent extraction error: {e}")
            raise
    
    def _extract_intent_with_patterns(self, text: str) -> Dict:
        """Extract intent using regex patterns"""
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return {
                        "intent": intent,
                        "method": "patterns",
                        "confidence": 0.7
                    }
        
        return {
            "intent": "unknown",
            "method": "patterns", 
            "confidence": 0.1
        }
    
    def _extract_entities(self, text: str, language: str) -> Dict:
        """Extract named entities from text"""
        entities = {
            "applications": [],
            "files": [],
            "folders": [],
            "email_addresses": [],
            "file_paths": [],
            "parameters": {}
        }
        
        # Use spaCy NER if available
        nlp_model = self.nlp_en if language == "en" else self.nlp_hi
        if nlp_model:
            doc = nlp_model(text)
            for ent in doc.ents:
                if ent.label_ in ["PERSON", "ORG"]:
                    entities["applications"].append(ent.text)
                elif ent.label_ in ["PRODUCT", "GPE"]:
                    entities["files"].append(ent.text)
        
        # Pattern-based entity extraction
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if entity_type == "application_names":
                    entities["applications"].extend(matches)
                elif entity_type == "email_addresses":
                    entities["email_addresses"].extend(matches)
                elif entity_type == "file_paths":
                    entities["file_paths"].extend(matches)
        
        # Remove duplicates
        for key in entities:
            if isinstance(entities[key], list):
                entities[key] = list(set(entities[key]))
        
        return entities
    
    def _extract_parameters(self, text: str, intent: str, entities: Dict) -> Dict:
        """Extract additional parameters based on intent and entities"""
        parameters = {}
        
        if intent == "file_operation":
            # Extract file operation type
            if re.search(r"create|make|new", text, re.IGNORECASE):
                parameters["operation"] = "create"
            elif re.search(r"delete|remove", text, re.IGNORECASE):
                parameters["operation"] = "delete"
            elif re.search(r"move|transfer", text, re.IGNORECASE):
                parameters["operation"] = "move"
            elif re.search(r"copy|duplicate", text, re.IGNORECASE):
                parameters["operation"] = "copy"
        
        elif intent == "email_operation":
            # Extract email subject and content hints
            subject_match = re.search(r"with\\s+(.+?)(?:\\s+attachment|$)", text, re.IGNORECASE)
            if subject_match:
                parameters["subject_hint"] = subject_match.group(1)
        
        elif intent == "web_operation":
            # Extract search query or URL
            search_match = re.search(r"search\\s+(?:for\\s+)?['\"]?([^'\"]+)['\"]?", text, re.IGNORECASE)
            if search_match:
                parameters["search_query"] = search_match.group(1)
        
        # Extract common modifiers
        if re.search(r"all\\s+", text, re.IGNORECASE):
            parameters["apply_to_all"] = True
        
        if re.search(r"force|forcefully", text, re.IGNORECASE):
            parameters["force"] = True
        
        return parameters
    
    def _calculate_confidence(self, intent_result: Dict, entities: Dict) -> float:
        """Calculate overall confidence score"""
        base_confidence = intent_result.get("confidence", 0.5)
        
        # Boost confidence if entities were found
        entity_boost = 0.0
        total_entities = sum(len(v) if isinstance(v, list) else 1 for v in entities.values() if v)
        if total_entities > 0:
            entity_boost = min(0.2, total_entities * 0.1)
        
        # Reduce confidence for unknown intents
        if intent_result["intent"] == "unknown":
            base_confidence *= 0.5
        
        final_confidence = min(0.95, base_confidence + entity_boost)
        return round(final_confidence, 2)
    
    def _update_conversation_context(self, text: str, intent: str, entities: Dict):
        """Update conversation context for future reference"""
        context_entry = {
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "intent": intent,
            "entities": entities
        }
        
        self.conversation_context.append(context_entry)
        
        # Keep only recent context
        if len(self.conversation_context) > self.context_window:
            self.conversation_context.pop(0)
    
    def set_language(self, language: str):
        """Set the primary processing language"""
        self.primary_language = language
        self.logger.info(f"NLP primary language set to: {language}")
    
    def set_offline_mode(self, offline: bool):
        """Enable or disable offline mode"""
        self.offline_mode = offline
        self.logger.info(f"NLP offline mode: {'enabled' if offline else 'disabled'}")
    
    def get_processing_stats(self) -> Dict:
        """Get NLP processing statistics"""
        total = self.processing_stats["total_processed"]
        success_rate = (
            self.processing_stats["successful_extractions"] / total
            if total > 0 else 0
        )
        fallback_rate = (
            self.processing_stats["fallback_used"] / total
            if total > 0 else 0
        )
        
        return {
            **self.processing_stats,
            "success_rate": success_rate,
            "fallback_rate": fallback_rate,
            "context_entries": len(self.conversation_context)
        }
    
    def clear_context(self):
        """Clear conversation context"""
        self.conversation_context.clear()
        self.logger.info("Conversation context cleared")
    
    def export_context(self) -> List[Dict]:
        """Export current conversation context"""
        return self.conversation_context.copy()
    
    def import_context(self, context: List[Dict]):
        """Import conversation context"""
        self.conversation_context = context[-self.context_window:]
        self.logger.info(f"Imported {len(self.conversation_context)} context entries")