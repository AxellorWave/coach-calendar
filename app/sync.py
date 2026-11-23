from datetime import datetime

import vk_api

from app.calendar.actions import TZ, create_event, delete_event, edit_event, quiet_noops
from app.config import VK_PEER_ID
from app.logger import get_logger
from app.parser.message_parser import parse_message

logger = get_logger(__name__)

HISTORY_COUNT = 1000  # сколько последних сообщений сверять
VK_PAGE_SIZE = 200    # больше VK за один запрос не отдаёт


def _slot(name, session_type, date, time):
    return (name, session_type, f'{date} {time}')


def _build_actions(messages):
    actions = []
    active = {}

    for msg in messages:
        if msg.get('out'):
            continue
        # Историю чата (ссылки Телемоста и т.п.) при сверке в лог не пишем
        r = parse_message(msg.get('text', ''), warn_unknown=False)
        if not r:
            continue
        name, st = r['name'], r['session_type']

        if r['type'] == 'create':
            slot = _slot(name, st, r['date'], r['time'])
            active[slot] = len(actions)
            actions.append(['create', slot, False])

        elif r['type'] == 'delete':
            slot = _slot(name, st, r['date'], r['time'])
            if slot in active:
                actions[active.pop(slot)][2] = True
            actions.append(['delete', slot, False])

        elif r['type'] == 'edit':
            new = _slot(name, st, r['date_new'], r['time_new'])
            old = None
            if r['date_old']:
                old = _slot(name, st, r['date_old'], r['time_old'])
            else:
                msg_time = datetime.fromtimestamp(msg['date'], TZ)
                mine = [s for s in active if s[0] == name and s[1] == st]
                future = [s for s in mine
                          if TZ.localize(datetime.strptime(s[2], '%d-%m-%Y %H:%M')) >= msg_time]
                future.sort(key=lambda s: datetime.strptime(s[2], '%d-%m-%Y %H:%M'))
                old = future[0] if future else (mine[-1] if mine else None)

            if old in active:
                actions[active.pop(old)][2] = True
            active[new] = len(actions)
            actions.append(['edit', (old, new), False])

    result = []
    for kind, args, skip in actions:
        if not skip:
            result.append((kind, args))
        elif kind == 'edit' and args[0]:
            result.append(('delete', args[0]))
    return result


def _fetch_history(vk, total):
    # getHistory отдаёт сообщения от новых к старым, поэтому листаем
    # смещением, пока не наберём total или история не закончится.
    items = []
    while len(items) < total:
        count = min(VK_PAGE_SIZE, total - len(items))
        page = vk.messages.getHistory(peer_id=VK_PEER_ID, count=count, offset=len(items))['items']
        items.extend(page)
        if len(page) < count:
            break
    # Если во время листания пришло новое сообщение, страницы сдвигаются
    # и одно сообщение может попасть дважды — убираем повторы по id.
    seen = set()
    return [m for m in items if not (m['id'] in seen or seen.add(m['id']))]


def sync_calendar(vk: vk_api.vk_api.VkApiMethod) -> int | None:
    items = _fetch_history(vk, HISTORY_COUNT)
    if not items:
        return None
    messages = list(reversed(items))

    actions = _build_actions(messages)
    ok = 0
    with quiet_noops():
        for kind, args in actions:
            if kind == 'create':
                name, st, dt = args
                ok += bool(create_event(name, dt, st))
            elif kind == 'delete':
                name, st, dt = args
                ok += delete_event(name, dt, st) is True
            elif kind == 'edit':
                old, (name, st, new_dt) = args
                ok += bool(edit_event(name, old[2] if old else None, new_dt, st))

    logger.info(f'Сверка по {len(messages)} сообщениям: действий {len(actions)}, успешно {ok}')
    return messages[-1]['id']
