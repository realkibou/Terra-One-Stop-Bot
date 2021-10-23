#!/usr/bin/python3

# Terra SKD
from terra_sdk.core.numeric import Dec

# Other assets
from assets.Logging import Logger
import B_Config as config

# Other imports
from json import dump, load
from os import path
from datetime import datetime

class Cooldown:
    if config.Debug_mode: print(f'Cooldown Class loaded.')
    default_logger = Logger().default_logger

    def write_cooldown(self, cooldowns):
        with open('X_Cooldowns.json', 'w') as fp:
            # Stringify dates otherwise cannot be written into json
            cooldowns = dict((i, f'{cooldowns[i]:%Y-%m-%d %H:%M}') for i in cooldowns)
            self.default_logger.debug(f'[Script] {cooldowns} has been written to X_Cooldowns.json')
            dump(cooldowns, fp)
        fp.close

    async def read_cooldown(self):

        # If file does not exists create one and fill it with data
        if not path.isfile('X_Cooldowns.json'):
            with open('X_Cooldowns.json', 'w') as fp:
                self.default_logger.debug(f'[Script] X_Cooldowns.json did not exist, so it was created.')
            fp.close
            return {}
        
        try:
            f = open('X_Cooldowns.json')
            cooldowns = load(f)
            self.default_logger.debug(f'[Script] X_Cooldowns.json existed and has been read: {cooldowns}')
            f.close

            cooldowns = dict((i, datetime.strptime(cooldowns[i], '%Y-%m-%d %H:%M')) for i in cooldowns)
        
            return cooldowns
        except:
            # If there is anything wrong with the X_Cooldowns.json, it will just give an empty dict.
            return {}

class Prettify:
    if config.Debug_mode: print(f'Prettify Class loaded.')   

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