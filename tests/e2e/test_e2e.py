"""E2E-тести (Playwright) проти живого сервера.

Запуск:
    docker compose up -d --build
    venv/Scripts/python -m pip install -r requirements-dev.txt
    venv/Scripts/python -m playwright install chromium
    venv/Scripts/python -m pytest tests/e2e -v

Базову адресу можна змінити: E2E_BASE_URL=http://localhost:8000
Тести створюють одноразових користувачів із унікальними іменами.
"""
import os
import uuid

BASE = os.environ.get('E2E_BASE_URL', 'http://localhost:8000')
PWD = 'E2e-pass-123'


def unique(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:8]}'


def signup(page, username: str):
    page.goto(f'{BASE}/signup/')
    page.fill('input[name="username"]', username)
    page.fill('input[name="email"]', f'{username}@example.com')
    page.fill('input[name="password1"]', PWD)
    page.fill('input[name="password2"]', PWD)
    page.click('button:has-text("Створити акаунт")')
    page.wait_for_url(f'{BASE}/')
    return username


def test_home_page_and_google_button(page):
    page.goto(f'{BASE}/')
    assert page.locator('.hero h1').is_visible()
    page.goto(f'{BASE}/accounts/login/')
    assert page.locator('a:has-text("Google")').is_visible()


def test_signup_and_publish_post(page):
    signup(page, unique('poster'))
    page.goto(f'{BASE}/feed/')
    body = f'E2E пост {uuid.uuid4().hex[:6]}'
    page.fill('textarea[name="body"]', body)
    page.click('button:has-text("Опублікувати")')
    page.wait_for_url(f'{BASE}/feed/')
    assert page.locator(f'text={body}').first.is_visible()


def test_chat_realtime_between_two_users(browser):
    a_name, b_name = unique('alice'), unique('bob')
    ctx_a, ctx_b = browser.new_context(), browser.new_context()
    a, b = ctx_a.new_page(), ctx_b.new_page()
    try:
        signup(a, a_name)
        signup(b, b_name)

        # A надсилає запит у друзі B
        a.goto(f'{BASE}/u/{b_name}/')
        a.click('button:has-text("Додати в друзі")')

        # B приймає запит
        b.goto(f'{BASE}/friends/')
        b.click('button:has-text("Прийняти")')

        # A створює чат і вибирає B учасником
        a.goto(f'{BASE}/chats/new/')
        a.select_option('select[name="participants"]', label=b_name)
        a.click('button:has-text("Зберегти")')

        # B відкриває розмову і залишається на сторінці (live WS)
        b.goto(f'{BASE}/chats/')
        b.click('a:has-text("Груповий чат")')

        # A пише — B має побачити повідомлення без перезавантаження
        msg = f'Привіт, {b_name}, це WS-тест!'
        a.fill('textarea[name="body"]', msg)
        a.click('button:has-text("Надіслати")')
        b.wait_for_selector(f'text={msg}', timeout=15000)
    finally:
        ctx_a.close()
        ctx_b.close()
