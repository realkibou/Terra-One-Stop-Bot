#!/usr/bin/python3

# Terra SDK
from requests.exceptions import ConnectTimeout
from terra_sdk.client.lcd import LCDClient, AsyncLCDClient
from terra_sdk.key.mnemonic import MnemonicKey

# Other assets
from assets.Contact_addresses import Contract_addresses

# from assets.Queries import Queries
import B_Config as config
from httpx import get, ConnectError, ConnectTimeout

def get_terra_gas_prices(retry=0):
   
    try:
        r = get("https://fcd.terra.dev/v1/txs/gas_prices")
        r.raise_for_status()
        if r.status_code == 200:
            return r.json()
    
    except ConnectError as err:
        if retry < 1:
            retry +=1
            get_terra_gas_prices(retry)
        else:
            raise err
    except ConnectTimeout as err:
        if retry < 1:
            retry +=1
            get_terra_gas_prices(retry)
        else:
            raise err
  
class Terra:
    if config.Debug_mode: print(f'Terra Class loaded.')

    terra_gas_prices = get_terra_gas_prices()

    if config.NETWORK == 'MAINNET':
        chain_id = 'columbus-5'
        public_node_url = 'https://lcd.terra.dev'
        # tx_look_up = f'https://finder.terra.money/{chain_id}/tx/'
        contact_addresses = Contract_addresses.contact_addresses(network='MAINNET')
        rev_Contract_addresses = Contract_addresses.rev_contact_addresses(contact_addresses)

    else:
        chain_id = 'bombay-12'
        public_node_url = 'https://bombay-lcd.terra.dev'
        # tx_look_up = f'https://finder.terra.money/{chain_id}/tx/'
        contact_addresses = Contract_addresses.contact_addresses(network='bombay-12')
        rev_Contract_addresses = Contract_addresses.rev_contact_addresses(contact_addresses)


    # Contracts required
    mmMarket = contact_addresses['mmMarket']
    mmOverseer = contact_addresses['mmOverseer']
    aTerra = contact_addresses['aTerra']
    Mint = contact_addresses['Mint']
    Collateral_Oracle = contact_addresses['Collateral Oracle']
    MirrorStaking = contact_addresses['MirrorStaking']
    Lock = contact_addresses['Lock']
    Oracle = contact_addresses['Oracle']

    mirrorFarm = contact_addresses['mirrorFarm']
    anchorFarm = contact_addresses['anchorFarm']
    specFarm = contact_addresses['specFarm']
    pylonFarm = contact_addresses['pylonFarm']
    specgov = contact_addresses['specgov']

    Mirror_MIR_UST_Pair = contact_addresses['Mirror MIR-UST Pair']
    Mirror_MIR_UST_LP = contact_addresses['Mirror MIR-UST LP']
    Spectrum_SPEC_UST_Pair = contact_addresses['Spectrum SPEC-UST Pair']
    Spectrum_SPEC_UST_LP = contact_addresses['Spectrum SPEC-UST LP']
    Terraswap_ANC_UST_Pair = contact_addresses['terraswapAncUstPair']
    Terraswap_ANC_UST_LP = contact_addresses['terraswapAncUstLPToken']
    Nexus_PSI_UST_Pair = contact_addresses['Nexus Psi-UST Pair']

    SpectrumStaking = contact_addresses['SpectrumStaking']
    NexusnETHrewards = contact_addresses['NexusnETHrewards']

    SPEC_token = contact_addresses['SPEC']
    MIR_token = contact_addresses['MIR']
    ANC_token = contact_addresses['ANC']
    bETH_token = contact_addresses['bETH']
    bLuna_token = contact_addresses['bLUNA']
    mAAPL_token = contact_addresses['mAAPL']
    aUST_token = contact_addresses['aUST']
    PSI_token = contact_addresses['PSI']

    failed_tx_hash = contact_addresses['failed_tx_hash']
    success_tx_hash = contact_addresses['success_tx_hash']

    terra = LCDClient(
        chain_id=chain_id,
        url=public_node_url,
        gas_prices=terra_gas_prices['uusd']+"uusd",
        gas_adjustment=2)

    terra_async = AsyncLCDClient(
        chain_id=chain_id,
        url=public_node_url,
        gas_prices=terra_gas_prices['uusd']+"uusd",
        gas_adjustment=2)

    mk = MnemonicKey(mnemonic=config.mnemonic) # Desire wallet via passphrase
    wallet = terra.wallet(mk) # Define what wallet to use
    account_address = wallet.key.acc_address # Account Add