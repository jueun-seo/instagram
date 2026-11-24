from authlib.integrations.starlette_client import OAuth
from config import settings
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from starlette.requests import Request
from sqlalchemy import select
from models import User
from deps import SessionDep, password_hash
import secrets
from routers.auth import set_refresh_cookie

router = APIRouter(prefix='/api/auth', tags=['social'])
oauth = OAuth()

oauth.register(
  name='google',
  client_id=settings.GOOGLE_CLIENT_ID,
  client_secret=settings.GOOGLE_CLIENT_SECRET,
  server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
  client_kwargs={'scope': 'openid email profile'}
)

FRONTEND = 'http://localhost:5173'

def find_or_create_user(db, provider, provider_id, name):
    # 사용자 검색
    user = db.scalar(
        select(User)
        .where(User.provider == provider, User.provider_id == provider_id)
    )
    if user:
        return user

    # 아이디 겹치는지 확인
    username = name
    n = 0
    while db.scalar(select(User).where(User.username == username)):
        n += 1
        username = f'{name}{n}'

    # 새로운 유저 생성
    user = User(
        username=username,
        password_hash=password_hash.hash(secrets.token_hex(32)),
        provider=provider,
        provider_id=provider_id
    )
    db.add(user)
    db.commit()
    return user



@router.get("/google/login")
async def login_via_google(request: Request):
    redirect_uri = request.url_for('auth_via_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def auth_via_google(request: Request, db: SessionDep):
    try:
        token = await oauth.google.authorize_access_token(request)
    except:
        return RedirectResponse(f'{FRONTEND}/login?error=social')
    
    user = token['userinfo']

    provider_user = find_or_create_user(
        db,
        'google',
        info.get('sub'),
        info.get('email').split('@')[0]
    )
    response = RedirectResponse(FRONTEND)
    set_refresh_cookie(response, provider_user, db)
    return response