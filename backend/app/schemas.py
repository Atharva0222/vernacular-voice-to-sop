from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["hi", "mr"]


class TranscribeResponse(BaseModel):
    transcript: str
    detected_language: Language


class Step(BaseModel):
    step_number: int
    text: str
    is_safety_warning: bool
    icon: str


class StructureRequest(BaseModel):
    transcript: str
    language: Language


class SOPResponse(BaseModel):
    steps: list[Step] = Field(default_factory=list)


class TTSRequest(BaseModel):
    text: str
    language: Language


class TTSResponse(BaseModel):
    audio_url: str


class StepWithAudio(Step):
    audio_url: str


class SOPWithAudioResponse(BaseModel):
    transcript: str
    detected_language: Language
    steps: list[StepWithAudio]
