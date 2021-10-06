#!/usr/bin/python3

# Other assets
from assets.Logging import Logger

# Other imports
import json
import os
from datetime import datetime

class Cooldown:
    def __init__(self):
        self.default_logger = Logger().default_logger

    def write_cooldown(self, cooldowns):
        with open('X_Cooldowns.json', 'w') as fp:
            # Stringify dates otherwise cannot be written into json
            for index in cooldowns:
                cooldowns[index] = f'{cooldowns[index]:%Y-%m-%d %H:%M}'
            self.default_logger.debug(f'[Script] {cooldowns} has been written to X_Cooldowns.json')
            json.dump(cooldowns, fp)
        fp.close
        pass

    def read_cooldown(self):

        # If file does not exists create one and fill it with data
        if not os.path.isfile('X_Cooldowns.json'):
            with open('X_Cooldowns.json', 'w') as fp:
                self.default_logger.debug(f'[Script] X_Cooldowns.json did not exist, so it was created.')
            fp.close
            return {}
        
        try:
            f = open('X_Cooldowns.json')
            cooldowns = json.load(f)
            self.default_logger.debug(f'[Script] X_Cooldowns.json has been read: {cooldowns}')
            f.close

            for index in cooldowns:
                cooldowns[index] = datetime.strptime(cooldowns[index], '%Y-%m-%d %H:%M')
        
            return cooldowns
        except:
            # If there is anything wrong with the X_Cooldowns.json, it will just give an empty dict.
            return {}        
