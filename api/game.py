import collections
import contextlib
import sqlite3
import typing
import httpx
import asyncio
from fastapi.testclient import TestClient
from redis_connect import app
user_client = TestClient(app)
from validate import app
validate_client = TestClient(app)
from answer import app
answer_client = TestClient(app)
from stats import app
stats_client = TestClient(app)

from fastapi import FastAPI, Depends, Response, HTTPException, status
from pydantic import BaseModel, BaseSettings
from collections import OrderedDict


class Settings(BaseSettings):
    valid_words_database: str
    logging_config: str

    class Config:
        env_file = ".env"

class User(BaseModel):
    username: str

class Guess(BaseModel):
    user_id: str
    guess: str


def get_db():
    with contextlib.closing(sqlite3.connect(settings.valid_words_database)) as db:
        db.row_factory = sqlite3.Row
        yield db


def score(remaining: int, win):
    if not win: return 50
    return 100 * remaining + 1


settings = Settings()
app = FastAPI()

@app.post("/game/new")
def new_game(user: User):
    body = {'username': user.username}
    r = user_client.put('/start/', json={'username': user.username})
    data = r.json()
    return {"status": data['status'], "user_id": data['user_id'], "game_id": data['game_id']}

@app.post("/game/{game_id}")
def game_progress(guess: Guess, game_id: int):
    data = validate_client.put("/validate/", json={'word': guess.guess}).json()
    if (data['status'] != "Valid"): return {'status': "invalid", 'message': data['status']}
    data = user_client.put("/get_game/", json={'user_id': guess.user_id, 'game_id': game_id}).json()
    if (data['status'] != "Valid"): return {'status': "invalid", 'message': data['status']}
    remaining = data['remaining guesses']
    guesses = data['current guesses']
    if (remaining <= 0): return {"status": "invalid", "message": "Out of guesses!"}
    if (len(guess.guess) != 5): return {"status": "invalid", "message": "incorrect word length"}
    data = user_client.put("/make_guess/", json={'user_id': guess.user_id, 'game_id': game_id, 'guess': guess.guess}).json()
    remaining -= 1
    data = answer_client.put("/check/", json={'word': guess.guess}).json()
    if (data['correct']):
        stats_client.post("/finish/", {'user_id': guess.user_id, 'game_id': game_id,'guesses': guesses, 'won': True})
        return {'status': 'win', 'remaining': remaining, 'score': score(remaining, True)}
    elif remaining == 0:
        stats_client.post("/finish/", {'user_id': guess.user_id, 'game_id': game_id,'guesses': guesses, 'won': False})
        return {'status': 'lose', 'remaining': remaining, 'score': score(remaining, False)}
    else:
        return {'remaining': remaining, 'status': 'incorrect', 'letters': data['results']}





    


