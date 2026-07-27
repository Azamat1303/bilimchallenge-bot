# ai_service.py
import asyncio
from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone
from config import EMERGENT_LLM_KEY
import logging

logger = logging.getLogger(__name__)


class AIService:
    """AI Chat va IELTS Checker uchun service"""
    
    def __init__(self):
        self.api_key = EMERGENT_LLM_KEY
    
    async def chat(self, user_id: int, message: str) -> str:
        """
        Oddiy AI suhbat
        """
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"user_{user_id}",
                system_message="Siz yordamchi AI assistentsiz. O'zbek va ingliz tillarida javob bering. Foydalanuvchiga do'stona va tushunarli javob bering."
            ).with_model("gemini", "gemini-3-flash-preview")
            
            user_message = UserMessage(text=message)
            
            # Stream qilib javobni to'plash
            full_response = ""
            async for event in chat.stream_message(user_message):
                if isinstance(event, TextDelta):
                    full_response += event.content
                elif isinstance(event, StreamDone):
                    break
            
            return full_response.strip()
        
        except Exception as e:
            logger.error(f"AI Chat error: {e}")
            return "Kechirasiz, xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring."
    
    async def check_ielts_writing(self, essay: str, task_type: str = "Task 2") -> dict:
        """
        IELTS Writing ni tekshirish va batafsil feedback berish
        
        Returns:
            {
                'band': 7.0,
                'task_achievement': 'Feedback...',
                'coherence': 'Feedback...',
                'vocabulary': 'Feedback...',
                'grammar': 'Feedback...',
                'errors': ['Error 1', 'Error 2'],
                'suggestions': ['Suggestion 1', 'Suggestion 2']
            }
        """
        try:
            # IELTS Checker uchun maxsus prompt
            system_message = """Siz IELTS Writing ekspertisiz. 
Foydalanuvchi tomonidan yozilgan inshoni to'liq tahlil qiling va quyidagi formatta javob bering:

BAND: [0-9 oralig'ida band, masalan: 7.0]

TASK ACHIEVEMENT:
[Task Achievement bo'yicha batafsil tahlil va feedback]

COHERENCE & COHESION:
[Coherence va Cohesion bo'yicha tahlil]

LEXICAL RESOURCE:
[Vocabulary va so'z boyligi tahlili]

GRAMMATICAL RANGE & ACCURACY:
[Grammatika tahlili]

ASOSIY XATOLAR:
1. [Xato 1]
2. [Xato 2]
...

TAVSIYALAR:
1. [Tavsiya 1]
2. [Tavsiya 2]
...

Javobingizni o'zbek tilida bering, lekin grammatika xatolarini ingliz tilida ko'rsating."""

            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"ielts_check_{id(essay)}",
                system_message=system_message
            ).with_model("gemini", "gemini-3-flash-preview")
            
            prompt = f"""IELTS Writing {task_type} Inshoni tahlil qiling:

{essay}

Iltimos, yuqoridagi formatda batafsil feedback bering."""
            
            user_message = UserMessage(text=prompt)
            
            # Stream qilib javobni to'plash
            full_response = ""
            async for event in chat.stream_message(user_message):
                if isinstance(event, TextDelta):
                    full_response += event.content
                elif isinstance(event, StreamDone):
                    break
            
            # Parse qilish
            result = self._parse_ielts_response(full_response)
            return result
        
        except Exception as e:
            logger.error(f"IELTS Check error: {e}")
            return {
                'band': 0,
                'feedback': "Kechirasiz, xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.",
                'errors': [],
                'suggestions': []
            }
    
    def _parse_ielts_response(self, response: str) -> dict:
        """
        AI javobidan ma'lumotlarni parse qilish
        """
        result = {
            'band': 0.0,
            'task_achievement': '',
            'coherence': '',
            'vocabulary': '',
            'grammar': '',
            'errors': [],
            'suggestions': [],
            'full_feedback': response
        }
        
        try:
            # Band ni topish
            if "BAND:" in response:
                band_line = response.split("BAND:")[1].split("\n")[0].strip()
                try:
                    result['band'] = float(band_line)
                except:
                    result['band'] = 0.0
            
            # Har bir bo'limni parse qilish
            sections = {
                'TASK ACHIEVEMENT:': 'task_achievement',
                'COHERENCE & COHESION:': 'coherence',
                'LEXICAL RESOURCE:': 'vocabulary',
                'GRAMMATICAL RANGE & ACCURACY:': 'grammar'
            }
            
            for marker, key in sections.items():
                if marker in response:
                    parts = response.split(marker)
                    if len(parts) > 1:
                        # Keyingi bo'limgacha oling
                        content = parts[1].split('\n\n')[0].strip()
                        result[key] = content
            
            # Xatolar
            if "ASOSIY XATOLAR:" in response:
                errors_section = response.split("ASOSIY XATOLAR:")[1]
                if "TAVSIYALAR:" in errors_section:
                    errors_section = errors_section.split("TAVSIYALAR:")[0]
                
                errors = [line.strip() for line in errors_section.split('\n') if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith('-'))]
                result['errors'] = errors
            
            # Tavsiyalar
            if "TAVSIYALAR:" in response:
                suggestions_section = response.split("TAVSIYALAR:")[1]
                suggestions = [line.strip() for line in suggestions_section.split('\n') if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith('-'))]
                result['suggestions'] = suggestions
        
        except Exception as e:
            logger.error(f"Parse error: {e}")
        
        return result


# Global instance
ai_service = AIService()
