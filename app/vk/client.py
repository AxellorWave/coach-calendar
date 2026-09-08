import vk_api
from vk_api.longpoll import VkLongPoll
from app.config import VK_TOKEN

def get_vk_session():
    return vk_api.VkApi(token=VK_TOKEN)

def get_longpoll(vk_session: vk_api.VkApi):
    return VkLongPoll(vk_session)
