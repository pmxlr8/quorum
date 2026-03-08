from typing import Literal
from pydantic import BaseModel


class AudioInEvent(BaseModel):
    type: Literal['audio']
    data: str


class TextInEvent(BaseModel):
    type: Literal['text']
    text: str


class TurnCompleteInEvent(BaseModel):
    type: Literal['turn_complete']


class GrantSpeakingTurnInEvent(BaseModel):
    type: Literal['grant_speaking_turn']
    agent: str


class VoteInEvent(BaseModel):
    type: Literal['cast_vote']
    vote: Literal['yes', 'no', 'abstain']


class OutEvent(BaseModel):
    type: str
    payload: dict
