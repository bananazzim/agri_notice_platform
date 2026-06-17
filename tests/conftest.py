"""
pytest configuration and fixtures for testing.
"""
import os
import django
from django.conf import settings

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

import pytest
from django.test import Client
from django.contrib.auth.models import User


@pytest.fixture
def db_setup(db):
    """데이터베이스 초기 설정"""
    pass


@pytest.fixture
def client():
    """Django 테스트 클라이언트"""
    return Client()


@pytest.fixture
def admin_user(db):
    """관리자 사용자 생성"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def regular_user(db):
    """일반 사용자 생성"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(client, admin_user):
    """인증된 클라이언트"""
    client.login(username='admin', password='adminpass123')
    return client
