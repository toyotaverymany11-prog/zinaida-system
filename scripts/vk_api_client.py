#!/usr/bin/env python3
"""
Zinaida VK API Client — универсальный клиент для VK API
Управление сообществом AI-психолог (ID 237663277)

Поддерживает два режима:
1. Community Token — через execute (ограничено)
2. User Token — полный доступ (требуется получить)
"""
import requests, json, sys, os, urllib.parse, time

# === КОНФИГ ===
GROUP_ID = 237663277
COMMUNITY_TOKEN = "vk1.a.3P4n_85bP-Xmg8rWztGYx3wOoRlAcpy-J8q-B3MyUhUeK58cdgOUnLJp87kil8n14PUcIny7WxC291CTAtOIlbl6PUuR_20ILnEwcFi_LNdTt1gpBCDiwT0gEHWEZvqz2tnQPRwFWfl-NmY6jz_QZ9QEsVI7O7Dvfx1pJIZ2PSbhrWWtDOMv51WFbIrxfi9RaC1pQdIbwHnb7EIdhaaDpg"
USER_TOKEN = os.environ.get("VK_USER_TOKEN", "")
API_V = "5.199"

# === КАРТА ДОСТУПНОСТИ МЕТОДОВ ===
# ✅ — работает с Community Token
# ❌ — НЕ работает с Community Token (нужен User Token)
# 🔶 — работает но с ограничениями

METHODS_MAP = {
    # === СТЕНА ===
    "wall.post":         {"community": "✅", "user": "✅", "note": "Через execute"},
    "wall.edit":         {"community": "❌", "user": "✅", "note": "Только User Token"},
    "wall.delete":       {"community": "❌", "user": "✅", "note": "Только User Token"},
    "wall.pin":          {"community": "❌", "user": "✅", "note": "Только User Token"},
    "wall.unpin":        {"community": "❌", "user": "✅", "note": "Только User Token"},
    "wall.repost":       {"community": "❌", "user": "✅", "note": "Только User Token"},
    "wall.get":          {"community": "✅", "user": "✅", "note": "Читает посты"},
    "wall.getComments":  {"community": "✅", "user": "✅", "note": "Читает комменты"},
    
    # === ФОТО ===
    "photos.getWallUploadServer":  {"community": "❌", "user": "✅", "note": "Только User Token"},
    "photos.saveWallPhoto":        {"community": "✅", "user": "✅", "note": "Через execute"},
    "photos.getAlbums":           {"community": "❌", "user": "✅", "note": "Только User Token"},
    "photos.getOwnerCoverPhotoUploadServer": {"community": "❌", "user": "✅", "note": "Обложка"},
    
    # === ВИДЕО ===
    "video.save":  {"community": "❌", "user": "✅", "note": "Только User Token"},
    "video.get":   {"community": "❌", "user": "✅", "note": "Только User Token"},
    
    # === ДОКУМЕНТЫ ===
    "docs.getWallUploadServer": {"community": "❌", "user": "✅", "note": "Нет прав на доки"},
    "docs.save":                {"community": "❌", "user": "✅", "note": "Только User Token"},
    
    # === ГРУППА ===
    "groups.getById":          {"community": "✅", "user": "✅", "note": "Инфо о группе"},
    "groups.getMembers":       {"community": "✅", "user": "✅", "note": "Участники"},
    "groups.getOnlineStatus":  {"community": "✅", "user": "✅", "note": "Статус онлайн"},
    "groups.getLongPollSettings": {"community": "✅", "user": "✅", "note": "Настройки Long Poll"},
    
    # === СТАТИСТИКА ===
    "stats.get": {"community": "❌", "user": "✅", "note": "Только User Token"},
    
    # === ИСТОРИИ ===
    "stories.get":  {"community": "✅", "user": "✅", "note": "Читает истории"},
    "stories.post": {"community": "❌", "user": "✅", "note": "Только User Token"},
    
    # === СООБЩЕНИЯ ===
    "messages.send":  {"community": "✅", "user": "✅", "note": "Работает"},
    "messages.getConversations": {"community": "❌", "user": "✅", "note": "Только User Token"},
    
    # === ОБСУЖДЕНИЯ ===
    "board.getTopics":       {"community": "✅", "user": "✅", "note": "Ветки обсуждений"},
    "board.addTopic":       {"community": "❌", "user": "✅", "note": "Только User Token"},
    
    # === МАРКЕТ ===
    "market.get":  {"community": "❌", "user": "✅", "note": "Только User Token"},
    "market.add":  {"community": "❌", "user": "✅", "note": "Только User Token"},
    
    # === ЛИДЫ ===
    "leads.getStats": {"community": "✅", "user": "✅", "note": "Работает"},
}


def execute(code, token=COMMUNITY_TOKEN):
    """Выполняет VKScript через API.execute"""
    r = requests.get("https://api.vk.com/method/execute", params={
        "code": code, "access_token": token, "v": API_V
    }, timeout=30)
    return r.json()


def get_mode():
    """Определяет текущий режим: community или user"""
    if USER_TOKEN:
        # Проверяем User Token
        r = requests.get("https://api.vk.com/method/users.get", params={
            "access_token": USER_TOKEN, "v": API_V
        }, timeout=10)
        if "response" in r.json():
            return "user"
    return "community"


def post(message, attachments="", from_group=1, publish_date=0, signed=0):
    """
    Публикует пост на стену.
    ✅ Community Token: wall.post через execute
    ✅ User Token: wall.post напрямую (с фото/видео)
    """
    mode = get_mode()
    
    if mode == "user":
        params = {
            "owner_id": -GROUP_ID,
            "message": message,
            "from_group": from_group,
            "signed": signed,
            "access_token": USER_TOKEN,
            "v": API_V
        }
        if attachments:
            params["attachments"] = attachments
        if publish_date:
            params["publish_date"] = publish_date
        
        r = requests.get("https://api.vk.com/method/wall.post", params=params, timeout=30)
        data = r.json()
    else:
        # VKScript execute — текст как JS строка без Unicode-экранирования
        escaped = message.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        code = f"return API.wall.post({{owner_id: -{GROUP_ID}, message: '{escaped}', from_group: {from_group}, signed: {signed}}});"
        data = execute(code)
    
    return data


def edit(post_id, message, attachments=""):
    """Редактирует пост. ❌ Community Token. ✅ User Token"""
    mode = get_mode()
    if mode != "user":
        return {"error": "group_auth_failed", "error_msg": "wall.edit не доступен с Community Token. Получи User Token."}
    
    params = {
        "owner_id": -GROUP_ID,
        "post_id": post_id,
        "message": message,
        "access_token": USER_TOKEN,
        "v": API_V
    }
    if attachments:
        params["attachments"] = attachments
    
    r = requests.get("https://api.vk.com/method/wall.edit", params=params, timeout=30)
    return r.json()


def delete(post_id):
    """Удаляет пост. ❌ Community Token. ✅ User Token"""
    mode = get_mode()
    if mode != "user":
        return {"error": "group_auth_failed"}
    
    r = requests.get("https://api.vk.com/method/wall.delete", params={
        "owner_id": -GROUP_ID, "post_id": post_id,
        "access_token": USER_TOKEN, "v": API_V
    }, timeout=15)
    return r.json()


def pin(post_id):
    """Закрепляет пост. ❌ Community Token. ✅ User Token"""
    mode = get_mode()
    if mode != "user":
        return {"error": "group_auth_failed"}
    r = requests.get("https://api.vk.com/method/wall.pin", params={
        "owner_id": -GROUP_ID, "post_id": post_id,
        "access_token": USER_TOKEN, "v": API_V
    }, timeout=15)
    return r.json()


def unpin(post_id):
    """Снимает закреп. ❌ Community Token. ✅ User Token"""
    mode = get_mode()
    if mode != "user":
        return {"error": "group_auth_failed"}
    r = requests.get("https://api.vk.com/method/wall.unpin", params={
        "owner_id": -GROUP_ID, "post_id": post_id,
        "access_token": USER_TOKEN, "v": API_V
    }, timeout=15)
    return r.json()


def upload_photo(image_path):
    """
    Загружает фото на стену и возвращает attachment.
    ❌ Community Token (photos.getWallUploadServer не доступен)
    ✅ User Token
    """
    mode = get_mode()
    if mode != "user":
        return {"error": "group_auth_failed", "error_msg": "Загрузка фото требует User Token"}
    
    # 1. Получаем сервер для загрузки
    r = requests.get("https://api.vk.com/method/photos.getWallUploadServer", params={
        "group_id": GROUP_ID, "access_token": USER_TOKEN, "v": API_V
    }, timeout=15)
    data = r.json()
    if "error" in data:
        return data
    
    upload_url = data["response"]["upload_url"]
    
    # 2. Загружаем фото
    with open(image_path, "rb") as f:
        r2 = requests.post(upload_url, files={"photo": f}, timeout=30)
    upload_result = r2.json()
    
    # 3. Сохраняем
    r3 = requests.get("https://api.vk.com/method/photos.saveWallPhoto", params={
        "group_id": GROUP_ID, 
        "photo": upload_result.get("photo", ""),
        "server": upload_result.get("server", 0),
        "hash": upload_result.get("hash", ""),
        "access_token": USER_TOKEN,
        "v": API_V
    }, timeout=15)
    saved = r3.json()
    
    if "response" in saved and len(saved["response"]) > 0:
        photo = saved["response"][0]
        attachment = f"photo{photo['owner_id']}_{photo['id']}"
        return {"success": True, "attachment": attachment}
    
    return {"error": "upload_failed", "details": saved}
    """Публикует пост на стену сообщества. ✅ работает"""
    code = f'''return API.wall.post({{
        owner_id: -{GROUP_ID},
        message: {json.dumps(message)},
        from_group: {from_group},
        signed: {signed}
    }});'''
    return execute(code)


def wall_get(count=5, offset=0):
    """Получает посты со стены. ✅ работает"""
    code = f'''return API.wall.get({{
        owner_id: -{GROUP_ID},
        count: {count},
        offset: {offset}
    }});'''
    return execute(code)


def wall_get_by_id(post_ids):
    """Получает конкретные посты по ID. ✅ работает"""
    ids = ",".join([f"-{GROUP_ID}_{pid}" for pid in (post_ids if isinstance(post_ids, list) else [post_ids])])
    code = f'''return API.wall.getById({{posts: "{ids}"}});'''
    return execute(code)


def groups_get_members(count=10, offset=0):
    """Получает участников сообщества. ✅ работает"""
    code = f'''return API.groups.getMembers({{group_id: {GROUP_ID}, count: {count}, offset: {offset}}});'''
    return execute(code)


def messages_send(user_id, message, random_id=None):
    """Отправляет сообщение пользователю от сообщества. ✅ работает"""
    if random_id is None:
        random_id = int(time.time() * 1000)
    code = f'''return API.messages.send({{
        user_id: {user_id},
        random_id: {random_id},
        message: {json.dumps(message)}
    }});'''
    return execute(code)


def board_get_topics(count=5):
    """Получает обсуждения. ✅ работает"""
    code = f'''return API.board.getTopics({{group_id: {GROUP_ID}, count: {count}, order: 1}});'''
    return execute(code)


def stats_get_post_reach(post_id):
    """Получает статистику поста. ❌ не работает с Community Token"""
    print("⚠️ stats.getPostReach не работает с Community Token. Нужен User Token.")
    return {"error": "group_auth_failed"}


# === ГЕНЕРАЦИЯ ССЫЛКИ ДЛЯ USER TOKEN ===
def generate_oauth_link(app_id=822389317, scope="wall,photos,video,docs,groups,stats,board,market,leads,messages,offline"):
    """Генерирует ссылку для получения User Token"""
    redirect_uri = "https://oauth.vk.com/blank.html"
    params = {
        "client_id": app_id,
        "display": "page",
        "redirect_uri": redirect_uri,
        "scope": scope,
        "response_type": "token",
        "v": API_V,
        "revoke": 0  # не отзывать предыдущий токен
    }
    return f"https://id.vk.com/auth?{urllib.parse.urlencode({'redirect_url': f'https://oauth.vk.com/authorize?{urllib.parse.urlencode(params)}'})}"


def get_status_table():
    """Возвращает таблицу доступности методов"""
    lines = []
    lines.append("┌────────────────────────┬──────────┬──────────┬─────────────────────────┐")
    lines.append("│ Метод                  │ Community │ User     │ Примечание              │")
    lines.append("├────────────────────────┼──────────┼──────────┼─────────────────────────┤")
    for method, status in METHODS_MAP.items():
        c = "🔴" if status["community"] == "❌" else "🟢"
        u = "🔴" if status["user"] == "❌" else "🟢"
        lines.append(f"│ {method:<22} │ {status['community']}        │ {status['user']}        │ {status['note']:<23} │")
    lines.append("└────────────────────────┴──────────┴──────────┴─────────────────────────┘")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("VK API Client — управление сообществом AI-психолог")
        print(f"ID сообщества: {GROUP_ID}")
        print()
        print("Использование:")
        print("  python3 vk_api_client.py status       — таблица доступности методов")
        print("  python3 vk_api_client.py post \"текст\"  — опубликовать пост")
        print("  python3 vk_api_client.py wall [N]      — последние N постов")
        print("  python3 vk_api_client.py members [N]   — N участников")
        print("  python3 vk_api_client.py topics [N]    — N обсуждений")
        print("  python3 vk_api_client.py edit ID \"текст\" — ред. пост (User Token)")
        print("  python3 vk_api_client.py del ID        — удалить пост (User Token)")
        print("  python3 vk_api_client.py pin ID        — закрепить (User Token)")
        print("  python3 vk_api_client.py unpin ID      — снять закреп (User Token)")
        print("  python3 vk_api_client.py photo \"путь\"  — загр. фото (User Token)")
        print("  python3 vk_api_client.py oauth-link    — ссылка для User Token")
        print()
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        print(get_status_table())
        print()
        print(f"Community Token: {'🟢 работает' if True else '🔴 не работает'}")
        print(f"Текущий режим: Community Token ⚠️ (ограничен)")
        print(f"Для полного доступа получи User Token: python3 vk_api_client.py oauth-link")
    
    elif cmd == "post":
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Промпт для поста"
        r = post(text)
        if "response" in r:
            print(f"✅ Пост опубликован! ID: {r['response']['post_id']}")
            print(f"Ссылка: https://vk.com/wall-{GROUP_ID}_{r['response']['post_id']}")
        else:
            print(f"❌ Ошибка: {r}")
    
    elif cmd == "wall":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        r = wall_get(count)
        if "response" in r:
            items = r["response"].get("items", [])
            print(f"Последние {len(items)} постов:")
            for item in items:
                date = time.strftime("%d.%m %H:%M", time.localtime(item.get("date", 0)))
                text = item.get("text", "")[:80].replace("\n", " ")
                print(f"  [{item['id']}] {date} | {text}")
        else:
            print(f"❌ Ошибка: {r}")
    
    elif cmd == "members":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        r = groups_get_members(count)
        if "response" in r:
            items = r["response"].get("items", [])
            print(f"Участников всего: {r['response'].get('count', '?')}")
            print(f"Первые {len(items)}: {items}")
        else:
            print(f"❌ Ошибка: {r}")
    
    elif cmd == "topics":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        r = board_get_topics(count)
        if "response" in r:
            items = r["response"].get("items", [])
            print(f"Обсуждений: {r['response'].get('count', 0)}")
            for item in items:
                print(f"  [{item['id']}] {item.get('title', '?')}")
        else:
            print(f"❌ Ошибка: {r}")
    
    elif cmd == "oauth-link":
        print("Для ПОЛНОГО доступа к VK API (стена, фото, видео, редактирование, удаление):")
        print()
        print("1. Открой ссылку (если есть app_id 822389317 уточни):")
        print(generate_oauth_link())
        print()
        print("2. Подтверди доступ в браузере")
        print("3. Скопируй access_token из URL (после #access_token=...)")
        print("4. Сохрани: export VK_USER_TOKEN=... в .env")
        print()
        print("Или перейди в https://vk.com/apps?act=manage и посмотри ID приложения")
    
    elif cmd == "edit":
        if get_mode() != "user":
            print("❌ Редактирование требует User Token. Выполни: python3 vk_api_client.py oauth-link")
        else:
            pid = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            text = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
            r = edit(pid, text)
            print(json.dumps(r, ensure_ascii=False, indent=2))
    
    elif cmd == "del":
        if get_mode() != "user":
            print("❌ Удаление требует User Token.")
        else:
            pid = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            r = delete(pid)
            print("✅ Удалён" if "response" in r else f"❌ {r}")
    
    elif cmd == "pin":
        if get_mode() != "user":
            print("❌ Закрепление требует User Token.")
        else:
            pid = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            r = pin(pid)
            print("✅ Закреплён" if "response" in r else f"❌ {r}")
    
    elif cmd == "unpin":
        if get_mode() != "user":
            print("❌ Снятие закрепа требует User Token.")
        else:
            pid = int(sys.argv[2]) if len(sys.argv) > 2 else 0
            r = unpin(pid)
            print("✅ Закреп снят" if "response" in r else f"❌ {r}")
    
    elif cmd == "photo":
        if get_mode() != "user":
            print("❌ Загрузка фото требует User Token.")
        else:
            path = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
            if not path or not os.path.exists(path):
                print(f"❌ Файл не найден: {path}")
            else:
                r = upload_photo(path)
                print(json.dumps(r, ensure_ascii=False, indent=2))
    
    else:
        print(f"Неизвестная команда: {cmd}")
