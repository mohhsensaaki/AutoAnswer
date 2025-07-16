import io
import os
import base64
import requests
from common.log_creator import create_logger
from pathlib import Path
from openai import OpenAI
from fastapi import HTTPException
from urllib.parse import urlparse

# Global configuration
is_production = os.getenv("IS_PRODUCTION", "no")
audio_model = os.getenv("AUDIO_MODEL", "gpt-4o-mini-transcribe")
bearer_token = os.getenv(
    "CORE_BEARER_TOKEN",
    "Bearer v3.local.wYPMAsWypky3h10FUVrtnyJNTlbgzTifUfvzt1w-h7Xl82n10Tt7E3jmx8OE-2rNpnJabA38nhosohSggMB-lNnczNvA7aRsdv3P5KW9wDD6pn7ERnfdst7B8Zx3yeAXdg-fiBuil-gXkGnuWjtOBIN-65KP5rL1z2E.djEt",
)
issue_msg = "I can not listen to your voice, could you please write your content."
log_url = os.getenv("LOG_URL", ".")
logger = create_logger(is_production, log_url)

def _get_openai_client() -> OpenAI:
    """
    Initializes and returns the OpenAI client using the API key.
    """
    openai_api_key = os.getenv(
        "OPENAI_API_KEY",
        "sk-Xp0TePLM7Yq33EPYTpc0fS5XWUQEc5Y3k-I5wnUP3xT3BlbkFJ1gnJs6GiIm_SxWgw8tfqTBnfjI1DWoD0mrZ2yH190A",
    )
    if not openai_api_key:
        logger.error("Missing OpenAI API key.")
        raise ValueError("Missing OpenAI API key.")
    return OpenAI(api_key=openai_api_key)


def _transcribe_audio_bytes(file_binary: bytes, filename: str = "audio.m4a") -> str:
    """
    Shared helper function that transcribes audio from binary data.
    
    :param file_binary: The audio file's binary content.
    :param filename: The filename to use for the audio file (defaults to "audio.m4a").
    :return: Transcribed text on success or issue_msg on failure.
    """
    try:
        # Wrap the binary data in an in-memory file and assign a filename (required by the API)
        audio_file = io.BytesIO(file_binary)
        audio_file.name = filename
    except Exception as e:
        logger.error(f"Error creating audio file: {e}")
        return issue_msg

    try:
        client = _get_openai_client()
        transcription = client.audio.transcriptions.create(
            model=audio_model, file=audio_file
        )
        logger.info(f"audio tranciption is: {transcription}")
        return transcription.text
    except Exception as e:
        logger.error(f"ASR Error during transcription: {e}")
        return issue_msg


def transcribe_audio_url(audio_url: str) -> str:
    """
    Fetches audio from a URL (using a Bearer token) and transcribes it.
    
    :param audio_url: The URL of the audio file.
    :return: Transcription text on success or issue_msg on failure.
    """
    headers = {"Authorization": f"Bearer {bearer_token}"}
    try:
        response = requests.get(audio_url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"ASR Error fetching audio from URL: {e}")
        return issue_msg

    file_binary = response.content
    
    # Extract filename from URL, fallback to default if not available
    try:
        parsed_url = urlparse(audio_url)
        filename = os.path.basename(parsed_url.path) if parsed_url.path else "audio.m4a"
        if not filename or filename == "/":
            filename = "audio.m4a"
    except Exception:
        filename = "audio.m4a"
    
    return _transcribe_audio_bytes(file_binary, filename)


def transcribe_audio_base64(audio_base64: str) -> str:
    """
    Decodes a base64-encoded audio string and transcribes it.
    
    :param audio_base64: The base64-encoded audio data.
    :return: Transcription text on success or issue_msg on failure.
    """
    try:
        file_binary = base64.b64decode(audio_base64)
    except Exception as e:
        logger.error(f"Base64 decoding error: {e}")
        return issue_msg

    # Detect audio format from binary data and generate appropriate filename
    filename = _detect_audio_format(file_binary)
    
    return _transcribe_audio_bytes(file_binary, filename)


def _detect_audio_format(file_binary: bytes) -> str:
    """
    Detect audio format from binary data and return appropriate filename.
    
    :param file_binary: The audio file's binary content.
    :return: Filename with appropriate extension based on detected format.
    """
    # Check for common audio file signatures (magic numbers)
    if len(file_binary) < 12:
        return "audio.m4a"  # Default fallback
    
    # Check for various audio formats by their file signatures
    if file_binary[:4] == b'ftyp' or file_binary[4:8] == b'ftyp':
        # M4A/MP4 audio
        return "audio.m4a"
    elif file_binary[:3] == b'ID3' or file_binary[:2] == b'\xff\xfb' or file_binary[:2] == b'\xff\xf3' or file_binary[:2] == b'\xff\xf2':
        # MP3 audio
        return "audio.mp3"
    elif file_binary[:4] == b'RIFF' and file_binary[8:12] == b'WAVE':
        # WAV audio
        return "audio.wav"
    elif file_binary[:4] == b'OggS':
        # OGG audio
        return "audio.ogg"
    elif file_binary[:4] == b'fLaC':
        # FLAC audio
        return "audio.flac"
    elif file_binary[:3] == b'\xff\xe0' or file_binary[:2] == b'\xff\xe0':
        # Another MP3 variant
        return "audio.mp3"
    elif file_binary[:8] == b'FORM' and file_binary[8:12] == b'AIFF':
        # AIFF audio
        return "audio.aiff"
    elif file_binary[:4] == b'wvpk':
        # WavPack audio
        return "audio.wv"
    else:
        # Default fallback
        return "audio.m4a"


def transcribe_audio_file(file_path: str) -> str:
    """
    Reads an audio file from the given file path and transcribes it.

    :param file_path: Path to the audio file.
    :return: Transcription text on success or issue_msg on failure.
    """
    try:
        with open(file_path, "rb") as f:
            file_binary = f.read()
    except Exception as e:
        logger.error(f"Error reading audio file: {e}")
        return issue_msg
    
    # Extract filename from the file path
    filename = os.path.basename(file_path)
    return _transcribe_audio_bytes(file_binary, filename)

if __name__ == "__main__":
    """import argparse
    logger.info(f"audio model is: {audio_model}")
    parser = argparse.ArgumentParser(description="Test ASR transcription.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--url', type=str, help='Audio file URL to transcribe')
    group.add_argument('--base64', type=str, help='Base64-encoded audio string to transcribe')
    group.add_argument('--file', type=str, help='Path to local audio file to transcribe')
    args = parser.parse_args()"""
    args = {
        "url": None,
        "base64": "",
        "file": "C:/Users/EBS - 03.07/Documents/Sound recordings/Recording (2).m4a"
    }
    if args["url"]:
        print("Transcribing from URL...")
        result = transcribe_audio_url(args["url"])
        print("Transcription result:", result)
    elif args["base64"]:
        print("Transcribing from base64 string...")
        result = transcribe_audio_base64(args["base64"])
        print("Transcription result:", result)
    elif args["file"]:
        print("Transcribing from local file...")
        result = transcribe_audio_file(args["file"])
        print("Transcription result:", result)
