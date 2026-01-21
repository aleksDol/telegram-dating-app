# models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


@dataclass
class User:
    user_id: int
    username: Optional[str]
    name: str
    age: int
    gender: str
    city: Optional[str]
    relationship_status: Optional[str]
    photo: Optional[str]
    purpose: str = "куда-то сходить"
    points: int = 0
    reg_date: Optional[str] = None
    last_active: Optional[str] = None
    favorite_categories: List[str] = None
    referral_code: Optional[str] = None
    referred_by: Optional[int] = None
    referrals_count: int = 0
    is_banned: bool = False
    ban_reason: Optional[str] = None
    banned_date: Optional[str] = None

    def __post_init__(self):
        if self.favorite_categories is None:
            self.favorite_categories = []
        if not self.reg_date:
            self.reg_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Создание пользователя из словаря БД"""
        favorite_categories = []
        if data.get('favorite_categories'):
            try:
                favorite_categories = json.loads(data['favorite_categories'])
            except:
                favorite_categories = []

        return cls(
            user_id=data['user_id'],
            username=data.get('username'),
            name=data['name'],
            age=data['age'],
            gender=data['gender'],
            city=data.get('city'),
            relationship_status=data.get('relationship_status'),
            photo=data.get('photo'),
            purpose=data.get('purpose', 'куда-то сходить'),
            points=data.get('points', 0),
            reg_date=data.get('reg_date'),
            last_active=data.get('last_active'),
            favorite_categories=favorite_categories,
            referral_code=data.get('referral_code'),
            referred_by=data.get('referred_by'),
            referrals_count=data.get('referrals_count', 0),
            is_banned=bool(data.get('is_banned', 0)),
            ban_reason=data.get('ban_reason'),
            banned_date=data.get('banned_date')
        )


@dataclass
class Event:
    id: Optional[int]
    user_id: int
    title: str
    description: str
    event_date: str
    target_gender: str = "Все"
    city: str
    category: Optional[str] = None
    created: Optional[str] = None
    is_hidden: bool = False

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def from_dict(cls, data: dict) -> 'Event':
        """Создание события из словаря БД"""
        return cls(
            id=data.get('id'),
            user_id=data['user_id'],
            title=data['title'],
            description=data['description'],
            event_date=data['event_date'],
            target_gender=data.get('target_gender', 'Все'),
            city=data['city'],
            category=data.get('category'),
            created=data.get('created'),
            is_hidden=bool(data.get('is_hidden', 0))
        )


@dataclass
class Like:
    id: Optional[int]
    from_user: int
    to_user: int
    event_id: int
    mutual: bool = False
    created: Optional[str] = None

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
