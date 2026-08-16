"""Сиілка демо-даних: реалістичні користувачі, пости, групи, чати, події.

    manage.py seed_demo --clean   # видалити сміття від E2E-прогонів
    manage.py seed_demo           # засіяти демо-контент (ідемпотентно)

Демо-користувачі: пароль demo-pass-123.
"""
import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from network.models import (Comment, Conversation, Event, Follow, Friendship,
                            Group, Like, Membership, Message, Notification,
                            Post, Profile, Rating)

E2E_JUNK = re.compile(r'^(alice|bob|clara|poster)_[0-9a-f]{8}$|^dbguser\d+$')
DEMO_PASSWORD = 'demo-pass-123'

PEOPLE = [
    # username, ім'я, біо, pravatar
    ('olesya_k', 'Олеся Ковальчук', 'Кава, код і Карпати. Frontend у Львові.', 47),
    ('bodryn', 'Богдан Ринда', 'Фотографую Львів і людей у ньому. Плівка > цифра.', 12),
    ('marichka_dev', 'Марічка Савка', 'Python-розробниця. Django, чай і коти.', 32),
    ('dmytro_h', 'Дмитро Гнатюк', 'Бігу марафони, читаю фантастику, пишу бекенд.', 58),
    ('solomia_v', 'Соломія Волошок', 'Ілюструю книжки та малюю Карпати.', 25),
    ('taras_b', 'Тарас Багрій', 'Гітара, OK Go і щоп' + 'ятничні джеми.', 15),
    ('yaryna_p', 'Ярина Петлюк', 'Веду книжковий клуб «Сторінка». Читаю 52 книжки на рік.', 41),
    ('andrii_m', 'Андрій Мельник', 'Гори — моя стихія. Тури Карпатами щомісяця.', 68),
]

POSTS = [
    # author, body, media_url, group, години тому
    ('olesya_k', 'Здала проєкт, вирушила на вихідні в Верховину. Інтернет ловить тільки на пагорбі — і це найкращий детокс 🏔️', 'https://picsum.photos/seed/verhovyna/1200/700', None, 3),
    ('bodryn', 'Ранковий Львів у тумані. Плівка Portra 400 ніколи не підводить.', 'https://picsum.photos/seed/lviv-fog/1200/700', 'Львів у кадрі', 7),
    ('marichka_dev', 'Доступно пояснила новачкам, чому ORM — це не магія, а просто зручний SQL. Запис мітапу вже на каналі.', 'https://www.youtube.com/watch?v=mZbUKpY4Dpc', None, 12),
    ('dmytro_h', '42 км за 3:47. Особистий рекорд! Дякую всім, хто вітав на фініші — ви найкращі 🏃', 'https://picsum.photos/seed/marathon/1200/700', None, 26),
    ('solomia_v', 'Фінальний розворот для казки про гірського духа. Акварель + лінер, шість годин роботи.', 'https://picsum.photos/seed/illustration/1200/700', None, 30),
    ('taras_b', 'Наш джем-бенд шукає барабанщика у Львові. Репетиції щовівторка, матеріал свій.', '', None, 44),
    ('yaryna_p', 'Цього місяця читали Франсуазу Саган. Наступна зустріч клубу — дивіться у подіях!', '', 'Книжковий клуб «Сторінка»', 50),
    ('andrii_m', 'Маршрут на Говерлу через Брескул: 14 км, 1200 м набору. Класика, яка ніколи не набридає.', 'https://picsum.photos/seed/hoverla/1200/700', 'Карпатські мандрівники', 55),
    ('marichka_dev', 'Django 6 вражає: асинхронні views з коробки — те, чого ми всі чекали. Хто вже пробував у бою?', '', 'Python Україна', 60),
    ('dmytro_h', 'Порівняння п' + 'яти рендерів шаблонізаторів у Python — surprise: Jinja не завжди швидша. Таблиця в коментарях.', 'https://dou.ua/', 'Python Україна', 70),
    ('bodryn', 'Друзі, збираю фотоісторію про львівських кав' + 'ярні. Пишіть, кого додати до списку!', '', 'Львів у кадрі', 80),
    ('olesya_k', 'Мій топ-3 кави у Львові цього сезону: «Штіль», «Кредо», і та маленька на Ринку, де завжди черга. Ваші?', '', None, 95),
]


EXTRAS={'olesya_k':('Львів','Кава, код, Карпати — у такому порядку'),'bodryn':('Львів','Шукаю світло завжди і всюди'),'marichka_dev':('Київ','Пишу на Django, годування котів у перервах'),'dmytro_h':('Харків','Наступна ціль — ультрамарафон'),'solomia_v':('Івано-Франківськ','Малюю гори, поки не побачу море'),'taras_b':('Львів','Новий трек уже скоро'),'yaryna_p':('Тернопіль','Книга місяця: «Більше повітря»'),'andrii_m':('Львів','Збираю рюкзак у гори')}
class Command(BaseCommand):
    help = 'Сиілка реалістичного демо-контенту (ідемпотентно) / чистка E2E-сміття (--clean)'

    def add_arguments(self, parser):
        parser.add_argument('--clean', action='store_true', help='видалити користувачів, створених E2E-тестами')

    def handle(self, *args, **options):
        if options['clean']:
            junk = [u for u in User.objects.all() if E2E_JUNK.match(u.username)]
            for u in junk:
                u.delete()
            self.stdout.write(self.style.WARNING(f'Видалено {len(junk)} E2E-користувачів (пости/чати каскадно).'))
            return
        if User.objects.filter(username='olesya_k').exists():
            self.stdout.write('Демо-дані вже засіяні — нічого не роблю.')
            return
        if not User.objects.filter(is_superuser=True).exists():
            admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin1234!')
            Profile.objects.create(user=admin, bio='Адміністратор платформи')
            self.stdout.write(self.style.WARNING('Створено суперкористувача: admin / admin1234!'))
        now = timezone.now()
        users = {}
        for username, full, bio, img in PEOPLE:
            first, last = full.split(' ', 1)
            u = User.objects.create_user(username, f'{username}@uasocial.ua', DEMO_PASSWORD, first_name=first, last_name=last)
            loc, st = EXTRAS.get(username, ('', ''))
            Profile.objects.create(user=u, bio=bio, avatar=f'https://i.pravatar.cc/200?img={img}',
                                   cover=f'https://picsum.photos/seed/{username}-cover/1200/300', location=loc, status=st)
            users[username] = u
        nazar = User.objects.filter(username='nazar').first()
        groups = {}
        for name, owner, desc in [
            ('Python Україна', 'marichka_dev', 'Спільнота українських Python-розробників: новини, вакансії, мітипи.'),
            ('Книжковий клуб «Сторінка»', 'yaryna_p', 'Читаємо разом українську та світову класику, зустрічаємось щомісяця.'),
            ('Карпатські мандрівники', 'andrii_m', 'Походи, маршрути, спорядження. Новачкам раді!'),
            ('Львів у кадрі', 'bodryn', 'Фотоспільнота міста: прогулянки, плівка, спільні виставки.'),
        ]:
            g = Group.objects.create(name=name, description=desc, owner=users[owner])
            Membership.objects.create(user=users[owner], group=g, is_admin=True)
            groups[name] = g
        for uname, gname in [('olesya_k', 'Python Україна'), ('marichka_dev', 'Python Україна'), ('dmytro_h', 'Python Україна'), ('taras_b', 'Python Україна'), ('solomia_v', 'Карпатські мандрівники'), ('olesya_k', 'Львів у кадрі')]:
            Membership.objects.get_or_create(user=users[uname], group=groups[gname])
        posts = []
        for author, body, media, gname, hours in POSTS:
            p = Post.objects.create(author=users[author], body=body, media_url=media, group=groups[gname] if gname else None)
            Post.objects.filter(pk=p.pk).update(created_at=now - timedelta(hours=hours))
            posts.append(p)
        for a, b in [('olesya_k', 'marichka_dev'), ('bodryn', 'olesya_k'), ('dmytro_h', 'andrii_m'), ('taras_b', 'solomia_v'), ('yaryna_p', 'bodryn')]:
            Friendship.objects.create(sender=users[a], receiver=users[b], status='accepted')
        for fan, star in [('dmytro_h', 'olesya_k'), ('taras_b', 'marichka_dev'), ('yaryna_p', 'solomia_v'), ('bodryn', 'andrii_m')]:
            Follow.objects.create(follower=users[fan], target=users[star])
        like_map = {0: ['marichka_dev', 'bodryn', 'solomia_v'], 2: ['olesya_k', 'dmytro_h', 'taras_b', 'yaryna_p'], 3: ['olesya_k', 'andrii_m'], 4: ['yaryna_p', 'taras_b'], 7: ['solomia_v', 'dmytro_h'], 8: ['dmytro_h', 'taras_b', 'bodryn'], 11: ['marichka_dev', 'yaryna_p', 'bodryn']}
        for idx, fans in like_map.items():
            for f in fans:
                Like.objects.create(user=users[f], post=posts[idx])
        for idx, author, body in [
            (0, 'marichka_dev', 'Верховина — топ! Передай привіт горам 🙌'),
            (0, 'bodryn', 'Фото з пагорба буде?'),
            (2, 'dmytro_h', 'Дякую за пояснення, нарешті зрозумів select_related!'),
            (3, 'olesya_k', 'Вітаю з рекордом! 💪'),
            (8, 'taras_b', 'Спробував — асинхронні вьюхи працюють як годинник.'),
            (11, 'solomia_v', 'Додай «Кредо» — там найкращий фільтр на місті.'),
        ]:
            Comment.objects.create(user=users[author], post=posts[idx], body=body)
        for idx, uname in [(2, 'dmytro_h'), (8, 'olesya_k'), (7, 'taras_b')]:
            share = Post.objects.create(author=users[uname], shared_from=posts[idx], body='Гарно сказано 👇' if idx != 7 else 'Хто зі мною наступного місяця?')
            Post.objects.filter(pk=share.pk).update(created_at=now - timedelta(hours=2))
        for idx, uname, val, rev in [(2, 'olesya_k', 5, 'Найкраще пояснення ORM українською!'), (8, 'bodryn', 5, ''), (11, 'marichka_dev', 4, 'Солідний список, згодна майже з усім.')]:
            Rating.objects.create(user=users[uname], post=posts[idx], value=val, review=rev)
        Rating.objects.create(user=users[uname := 'taras_b'], group=groups['Карпатські мандрівники'], value=5, review='Найактивніша гірська спільнота.')
        conv = Conversation.objects.create(title='')
        conv.participants.add(users['olesya_k'], users['marichka_dev'])
        for uname, body, mins in [('olesya_k', 'Маріч, ти на суботній мітип Python Україна?', 240), ('marichka_dev', 'Так! Виступаю з доповіддю про Channels 😅', 232), ('olesya_k', 'Оо, то тебе ганяти питаннями не буду, пожалію 😀', 228), ('marichka_dev', 'Навпаки — питай жорстко, так цікавіше!', 12)]:
            m = Message.objects.create(conversation=conv, sender=users[uname], body=body)
            Message.objects.filter(pk=m.pk).update(created_at=now - timedelta(minutes=mins))
        gconv = Conversation.objects.create(title='Вихідні в Карпатах')
        gconv.participants.add(users['andrii_m'], users['dmytro_h'], users['solomia_v'])
        for uname, body, mins in [('andrii_m', 'Збираюсь на Петрос 25-го. Маршрут уже є, компанія — ні.', 600), ('dmytro_h', 'Я в ділах, але душею з вами 🏔️', 590), ('solomia_v', 'Я за! Можу малювати на вершині, буде контент 😄', 300)]:
            m = Message.objects.create(conversation=gconv, sender=users[uname], body=body)
            Message.objects.filter(pk=m.pk).update(created_at=now - timedelta(minutes=mins))
        Event.objects.create(title='Мітап Python Україна: Channels у бою', description='Марічка Савка показує живий WebSocket-чат на Django Channels. Питання-відповіді після.', starts_at=now + timedelta(days=2), created_by=users['marichka_dev'])
        Event.objects.create(title='Зустріч книжкового клубу «Сторінка»', description='Обговорюємо «Більше повітря» Емини Бедрань. Кава і дискусії гарантовані.', starts_at=now + timedelta(days=9), created_by=users['yaryna_p'])
        Event.objects.create(title='Фотопрогулянка Львовом', description='Ранкове світло, Старий район, кава після. Плівка і цифра — усім раді.', starts_at=now + timedelta(days=16), created_by=users['bodryn'])
        Event.objects.create(title='Схід сонця на Говерлі', description='Нічний вихід підсвітлений ліхтарями — минулий захід, лишився в історії.', starts_at=now - timedelta(days=5), created_by=users['andrii_m'])
        if nazar:
            Friendship.objects.create(sender=users['olesya_k'], receiver=nazar, status='accepted')
            Friendship.objects.create(sender=users['marichka_dev'], receiver=nazar)  # pending — показати «Прийняти запит»
            Follow.objects.create(follower=users['bodryn'], target=nazar)
            Notification.objects.create(recipient=nazar, actor=users['olesya_k'], text='@olesya_k вподобав вашу публікацію')
            Notification.objects.create(recipient=nazar, actor=users['marichka_dev'], text='@marichka_dev прокоментував вашу публікацію', url='/feed/')
            Notification.objects.create(recipient=nazar, actor=users['marichka_dev'], text='@marichka_dev надіслав вам запит у друзі', url='/friends/')
        self.stdout.write(self.style.SUCCESS(
            f'Засіяно: {len(users)} користувачів, {len(posts)} постів, {len(groups)} груп, 2 чати, 4 події, рейтинг/поширення/коментарі/лайки. Пароль демо-юзерів: {DEMO_PASSWORD}'))
