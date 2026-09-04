from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.config import SECRET_KEY,APP_TITLE
from app.seed import init_db
from app.routers import auth,web,api
from pathlib import Path

BASE=Path(__file__).resolve().parent
app=FastAPI(title=APP_TITLE)
app.add_middleware(SessionMiddleware,secret_key=SECRET_KEY,max_age=8*60*60,same_site='lax',https_only=False)
app.mount('/static',StaticFiles(directory=str(BASE/'app'/'static')),name='static')
app.state.templates=Jinja2Templates(directory=str(BASE/'app'/'templates'))
app.include_router(auth.router); app.include_router(web.router); app.include_router(api.router)
@app.on_event('startup')
def startup(): init_db()
