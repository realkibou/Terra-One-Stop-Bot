# Other assets
import assets.Logging as logging_config

# Other imports
import logging.config
import json
import os
import io
from datetime import datetime

class Cooldown:
    def __init__(self):
        logging.config.dictConfig(logging_config.LOGGING_CONFIG)
        self.default_logger = logging.getLogger('default_logger')

        report_array = io.StringIO()
        report_handler = logging.StreamHandler(report_array)
        self.default_logger.addHandler(report_handler)

    def write_cooldown(self, cooldowns):
        # Input: Cooldowns list
        # Output: -
        # Action: Creates a file in the root folder, containing the last incl. date of the cooldown periode
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
            f = open('X_Cooldowns.json',)
            cooldowns = json.load(f)
            self.default_logger.debug(f'[Script] X_Cooldowns.json has been read: {cooldowns}')
            f.close

            for index in cooldowns:
                cooldowns[index] = datetime.strptime(cooldowns[index], '%Y-%m-%d %H:%M')
        except:
            # If there is anything wrong with the X_Cooldowns.json, it will just give an empty dict.
            return {}

        return cooldowns
