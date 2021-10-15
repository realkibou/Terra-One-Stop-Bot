#!/usr/bin/python3

# Terra SKD
from terra_sdk.core.numeric import Dec


# Other assets
from assets.Logging import Logger
import B_Config as config

# Other imports
import json
import os
from datetime import datetime

class Cooldown:
    if config.Debug_mode: print(f'Cooldown Class loaded.')
    default_logger = Logger().default_logger

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
            self.default_logger.debug(f'[Script] X_Cooldowns.json existed and has been read: {cooldowns}')
            f.close

            for index in cooldowns:
                cooldowns[index] = datetime.strptime(cooldowns[index], '%Y-%m-%d %H:%M')
        
            return cooldowns
        except:
            # If there is anything wrong with the X_Cooldowns.json, it will just give an empty dict.
            return {}

class Prettify:
    if config.Debug_mode: print(f'Prettify Class loaded.')
    def email_text_to_html(self):
        # Todo
        pass

    def value_convert_dec_to_float(self, input_value, human):

        if type(input_value) == Dec:
            # If you need a bigger number than 1000000, then you are way too rich lol
            if input_value > 1000000:
                if human:
                    output_value = f'{float(input_value / 1000000):.2f}'
                else:
                    output_value = input_value.__int__()
            else:
                output_value = f'{input_value.__float__():.2f}'
            
            return output_value
        else:    
            return input_value

    def dict_value_convert_dec_to_float(self, input_value, human=False):

        # Maybe its a list of dict
        if type(input_value) is list:
            output_value = []
            for item in input_value:
                output_value.append(dict((k, self.value_convert_dec_to_float(v, human)) for k, v in item.items()))
            return output_value

        # If it is just a plain dict
        elif type(input_value) is dict:
            return dict((k, self.value_convert_dec_to_float(v, human)) for k, v in input_value.items())