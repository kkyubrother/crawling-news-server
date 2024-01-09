import os
import random


def load_ua_list() -> list[str]:
    with open(os.path.join(os.getcwd(), "user-agents.txt"), encoding='utf-8') as f:
        return f.readlines()


__UA_LIST: list[str] = load_ua_list()


def get_header() -> dict:
    return {
        'User-Agent': random.choice(__UA_LIST).strip()
    }
