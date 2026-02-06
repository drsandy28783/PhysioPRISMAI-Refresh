"""
Azure Speech Services Client
Provides HIPAA-compliant speech-to-text transcription
"""

import os
import json
import base64
from typing import Dict, Optional
import azure.cognitiveservices.speech as speechsdk


class AzureSpeechClient:
    """
    Azure Speech Services client for voice transcription
    HIPAA-compliant (covered under Azure BAA)
    """

    def __init__(
        self,
        speech_key: str = None,
        speech_region: str = None,
        language: str = "en-US"
    ):
        """
        Initialize Azure Speech client

        Args:
            speech_key: Azure Speech API key
            speech_region: Azure region (e.g., 'eastus')
            language: Speech recognition language (default: en-US)
        """
        self.speech_key = speech_key or os.getenv('AZURE_SPEECH_KEY')
        self.speech_region = speech_region or os.getenv('AZURE_SPEECH_REGION', 'eastus')
        self.language = language

        if not self.speech_key or not self.speech_region:
            raise ValueError("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set")

        # Create speech config
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.speech_region
        )

        # Set recognition language
        self.speech_config.speech_recognition_language = self.language

        # Enable detailed output for better accuracy
        self.speech_config.output_format = speechsdk.OutputFormat.Detailed

        # Enable profanity filtering (optional for medical contexts)
        # self.speech_config.set_profanity(speechsdk.ProfanityOption.Raw)


    def transcribe_from_file(self, audio_file_path: str) -> Dict:
        """
        Transcribe audio from file

        Args:
            audio_file_path: Path to audio file (WAV, MP3, OGG)

        Returns:
            {
                'text': str,
                'confidence': float,
                'duration': float,
                'success': bool,
                'error': str (optional)
            }
        """
        try:
            # Create audio config from file
            audio_config = speechsdk.AudioConfig(filename=audio_file_path)

            # Create speech recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            # Perform recognition
            result = speech_recognizer.recognize_once()

            # Process result
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return {
                    'success': True,
                    'text': result.text,
                    'confidence': self._get_confidence(result),
                    'duration': result.duration.total_seconds() if result.duration else 0
                }
            elif result.reason == speechsdk.ResultReason.NoMatch:
                return {
                    'success': False,
                    'text': '',
                    'error': 'No speech could be recognized'
                }
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                return {
                    'success': False,
                    'text': '',
                    'error': f'Speech recognition canceled: {cancellation.reason}'
                }
            else:
                return {
                    'success': False,
                    'text': '',
                    'error': 'Unknown recognition error'
                }

        except Exception as e:
            return {
                'success': False,
                'text': '',
                'error': str(e)
            }


    def transcribe_from_blob(self, audio_blob: bytes, content_type: str = 'audio/wav') -> Dict:
        """
        Transcribe audio from binary blob (for web uploads)

        Args:
            audio_blob: Audio data as bytes
            content_type: MIME type of audio

        Returns:
            Same as transcribe_from_file()
        """
        try:
            # Save blob to temporary file
            import tempfile

            # Determine file extension from content type
            ext_map = {
                'audio/wav': '.wav',
                'audio/webm': '.webm',
                'audio/ogg': '.ogg',
                'audio/mp3': '.mp3',
                'audio/mpeg': '.mp3'
            }
            ext = ext_map.get(content_type, '.wav')

            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                temp_file.write(audio_blob)
                temp_path = temp_file.name

            # Transcribe from temp file
            result = self.transcribe_from_file(temp_path)

            # Clean up temp file
            try:
                os.remove(temp_path)
            except:
                pass

            return result

        except Exception as e:
            return {
                'success': False,
                'text': '',
                'error': str(e)
            }


    def transcribe_continuous(self, audio_file_path: str, callback=None) -> Dict:
        """
        Transcribe long audio with continuous recognition
        Useful for longer dictations (>30 seconds)

        Args:
            audio_file_path: Path to audio file
            callback: Optional callback function(text) called for each recognized phrase

        Returns:
            {
                'text': str (full transcript),
                'success': bool,
                'phrases': List[str]
            }
        """
        try:
            audio_config = speechsdk.AudioConfig(filename=audio_file_path)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            phrases = []
            done = False

            def recognized_cb(evt):
                if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    phrases.append(evt.result.text)
                    if callback:
                        callback(evt.result.text)

            def stop_cb(evt):
                nonlocal done
                done = True

            # Connect callbacks
            speech_recognizer.recognized.connect(recognized_cb)
            speech_recognizer.session_stopped.connect(stop_cb)
            speech_recognizer.canceled.connect(stop_cb)

            # Start continuous recognition
            speech_recognizer.start_continuous_recognition()

            # Wait for completion (with timeout)
            import time
            timeout = 300  # 5 minutes max
            start_time = time.time()
            while not done and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            speech_recognizer.stop_continuous_recognition()

            return {
                'success': True,
                'text': ' '.join(phrases),
                'phrases': phrases
            }

        except Exception as e:
            return {
                'success': False,
                'text': '',
                'error': str(e)
            }


    def _get_confidence(self, result) -> float:
        """
        Extract confidence score from detailed result

        Args:
            result: SpeechRecognitionResult

        Returns:
            Confidence score (0.0 - 1.0)
        """
        try:
            # Parse JSON from result
            if hasattr(result, 'json'):
                data = json.loads(result.json)
                if 'NBest' in data and len(data['NBest']) > 0:
                    return data['NBest'][0].get('Confidence', 0.0)
            return 0.9  # Default high confidence if not available
        except:
            return 0.9


    def get_supported_languages(self) -> list:
        """
        Get list of supported languages for speech recognition

        Returns:
            List of language codes
        """
        # Common languages for physiotherapy (can expand)
        return [
            'en-US',  # English (US)
            'en-GB',  # English (UK)
            'en-IN',  # English (India)
            'hi-IN',  # Hindi
            'ta-IN',  # Tamil
            'te-IN',  # Telugu
            'mr-IN',  # Marathi
            'bn-IN',  # Bengali
            'es-ES',  # Spanish
            'fr-FR',  # French
            'de-DE',  # German
        ]


def get_azure_speech_client(language: str = "en-US") -> AzureSpeechClient:
    """
    Factory function to get Azure Speech client instance

    Args:
        language: Speech recognition language

    Returns:
        AzureSpeechClient instance
    """
    return AzureSpeechClient(language=language)
