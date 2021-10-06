#!/usr/bin/python3

# Terra SDK
from terra_sdk.client.lcd import LCDClient
from terra_sdk.key.mnemonic import MnemonicKey

# Other assets
from assets.Contact_addresses import Contract_addresses

# from assets.Queries import Queries
import B_Config as config
import requests


# https://terra-money.github.io/terra-sdk-python/core_modules/wasm.html
class Terra:
    def __init__(self):

        if config.NETWORK == 'MAINNET':
            self.chain_id = 'columbus-5'
            self.public_node_url = 'https://lcd.terra.dev'
            self.tx_look_up = f'https://finder.terra.money/{self.chain_id}/tx/'            
            self.contact_addresses = Contract_addresses.contact_addresses(network='MAINNET')
            self.rev_Contract_addresses = Contract_addresses.rev_contact_addresses(self.contact_addresses)

        else:
            self.chain_id = 'bombay-12'
            self.public_node_url = 'https://bombay-lcd.terra.dev'
            self.tx_look_up = f'https://finder.terra.money/{self.chain_id}/tx/'
            self.contact_addresses = Contract_addresses.contact_addresses(network='bombay-12')
            self.rev_Contract_addresses = Contract_addresses.rev_contact_addresses(self.contact_addresses)

        # Contracts required
        self.mmMarket = self.contact_addresses['mmMarket']
        self.mmOverseer = self.contact_addresses['mmOverseer']
        self.aTerra = self.contact_addresses['aTerra']
        self.Mint = self.contact_addresses['Mint']
        self.Collateral_Oracle = self.contact_addresses['Collateral Oracle']
        self.Staking = self.contact_addresses['Staking']
        self.Lock = self.contact_addresses['Lock']
        self.Oracle = self.contact_addresses['Oracle']

        self.mirrorFarm = self.contact_addresses['mirrorFarm']
        self.anchorFarm = self.contact_addresses['anchorFarm']
        self.specFarm = self.contact_addresses['specFarm']
        self.pylonFarm = self.contact_addresses['pylonFarm']
        self.specgov = self.contact_addresses['specgov']

        self.Terraswap_MIR_UST_Pair = self.contact_addresses['Terraswap MIR-UST Pair']
        self.Spectrum_SPEC_UST_Pair = self.contact_addresses['Spectrum SPEC-UST Pair']
        self.Terraswap_ANC_UST_Pair = self.contact_addresses['terraswapAncUstPair']

        self.SPEC_token = self.contact_addresses['SPEC']
        self.MIR_token = self.contact_addresses['MIR']
        self.ANC_token = self.contact_addresses['ANC']
        self.bETH_token = self.contact_addresses['bETH']
        self.bLuna_token = self.contact_addresses['bLuna']
        self.mAAPL_token = self.contact_addresses['mAAPL']

        self.failed_tx_hash = self.contact_addresses['failed_tx_hash']
        self.success_tx_hash = self.contact_addresses['success_tx_hash']       

        def get_terra_gas_prices():
        # return json with gas prices in all native currencies in a human form - means 0.456 uusd for example
            try:
                r = requests.get("https://fcd.terra.dev/v1/txs/gas_prices")
                r.raise_for_status()
                if r.status_code == 200:
                    return r.json()
            except requests.exceptions.HTTPError as err:
                print(f"Could not fetch get_terra_gas_prices from Terra's FCD. Error message: {err}")

        self.terra = LCDClient(
            chain_id=self.chain_id,
            url=self.public_node_url,
            gas_prices=get_terra_gas_prices(),
            gas_adjustment=1.6)
        self.mk = MnemonicKey(mnemonic=config.mnemonic) # Desire wallet via passphrase
        self.wallet = self.terra.wallet(self.mk) # Define what wallet to use
        self.account_address = self.wallet.key.acc_address # Account Add
        
        ALL_rates = requests.get('https://api.extraterrestrial.money/v1/api/prices').json()
        self.ALL_rates = {**ALL_rates.pop('prices'), **ALL_rates}