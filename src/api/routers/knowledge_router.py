"""Knowledge API routes — tra cứu API ngoài an toàn cho trẻ (no-key + SafetyFilter).

Tất cả endpoint chỉ đọc, yêu cầu đăng nhập, và degrade mượt (nguồn lỗi → ok:false,
không 500). Logic nằm ở src/knowledge/knowledge_client.py.
"""

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.infrastructure.auth.auth import get_current_user
from src.knowledge import knowledge_client as kc


def _require_knowledge_enabled():
    """Công tắc admin KNOWLEDGE_ENABLED; mặc định BẬT khi chưa đặt."""
    if os.getenv("KNOWLEDGE_ENABLED", "").strip().lower() in {"0", "false", "no", "off"}:
        raise HTTPException(status_code=503, detail="API tri thức đang tắt")


router = APIRouter(dependencies=[Depends(_require_knowledge_enabled)])


@router.get("/api/knowledge/status")
async def knowledge_status(current_user: dict = Depends(get_current_user)):
    return kc.status()


# ── Học tập / Ngôn ngữ ──
@router.get("/api/knowledge/dictionary")
async def get_dictionary(
    word: str = Query(..., min_length=1, max_length=60),
    lang: str = Query("en", max_length=5),
    current_user: dict = Depends(get_current_user),
):
    return kc.dictionary(word, lang)


@router.get("/api/knowledge/country")
async def get_country(
    name: str = Query(..., min_length=1, max_length=60),
    current_user: dict = Depends(get_current_user),
):
    return kc.country(name)


@router.get("/api/knowledge/number-fact")
async def get_number_fact(
    number: Optional[str] = Query(None, max_length=20),
    current_user: dict = Depends(get_current_user),
):
    return kc.number_fact(number)


@router.get("/api/knowledge/math")
async def get_math(
    expr: str = Query(..., min_length=1, max_length=120),
    current_user: dict = Depends(get_current_user),
):
    return kc.math_eval(expr)


@router.get("/api/knowledge/trivia")
async def get_trivia(
    amount: int = Query(5, ge=1, le=20),
    category: Optional[int] = None,
    difficulty: Optional[str] = Query(None, max_length=10),
    current_user: dict = Depends(get_current_user),
):
    return kc.trivia(amount, category, difficulty)


# ── Đọc & Văn học ──
@router.get("/api/knowledge/books")
async def get_books(
    q: str = Query(..., min_length=1, max_length=80),
    current_user: dict = Depends(get_current_user),
):
    return kc.books(q)


@router.get("/api/knowledge/gutenberg")
async def get_gutenberg(
    q: str = Query(..., min_length=1, max_length=80),
    current_user: dict = Depends(get_current_user),
):
    return kc.gutenberg(q)


@router.get("/api/knowledge/poem")
async def get_poem(
    author: str = Query("", max_length=60),
    title: str = Query("", max_length=80),
    current_user: dict = Depends(get_current_user),
):
    return kc.poem(author, title)


@router.get("/api/knowledge/wiki")
async def get_wiki(
    q: str = Query(..., min_length=1, max_length=80),
    lang: str = Query("vi", max_length=5),
    current_user: dict = Depends(get_current_user),
):
    return kc.wiki(q, lang)


# ── Khoa học & Khám phá ──
@router.get("/api/knowledge/weather")
async def get_weather(
    city: str = Query(..., min_length=1, max_length=60),
    current_user: dict = Depends(get_current_user),
):
    return kc.weather(city)


@router.get("/api/knowledge/iss")
async def get_iss(current_user: dict = Depends(get_current_user)):
    return kc.iss()


@router.get("/api/knowledge/apod")
async def get_apod(current_user: dict = Depends(get_current_user)):
    return kc.apod()


@router.get("/api/knowledge/animal-fact")
async def get_animal_fact(
    kind: str = Query("cat", max_length=5),
    current_user: dict = Depends(get_current_user),
):
    return kc.animal_fact(kind)


@router.get("/api/knowledge/fun-fact")
async def get_fun_fact(current_user: dict = Depends(get_current_user)):
    return kc.fun_fact()


# ── Giải trí & Media ──
@router.get("/api/entertainment/jokes")
async def get_joke(
    type: str = Query("single", max_length=10),
    current_user: dict = Depends(get_current_user),
):
    return kc.joke(type)


@router.get("/api/knowledge/pokemon")
async def get_pokemon(
    name: str = Query(..., min_length=1, max_length=40),
    current_user: dict = Depends(get_current_user),
):
    return kc.pokemon(name)


@router.get("/api/knowledge/disney")
async def get_disney(
    name: str = Query(..., min_length=1, max_length=40),
    current_user: dict = Depends(get_current_user),
):
    return kc.disney(name)
