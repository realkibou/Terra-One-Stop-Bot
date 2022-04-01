#!/usr/bin/python3

# Terra SDK
import re
from terra_sdk.core.coins import Coin
from terra_sdk.core.numeric import Dec
from terra_sdk.exceptions import LCDResponseError

# Other assets
from assets.Terra import Terra
from assets.Logging import Logger
import B_Config as config
 
# Other imports
from datetime import datetime
from time import mktime, sleep
from re import search
import asyncio

account_address = Terra.account_address

class Queries:
    if config.Debug_mode: print(f'Queries Class loaded.')
    default_logger = Logger().default_logger

    def __init__(self) -> None:
        self.all_rates = asyncio.run(self.get_all_rates())
       
    async def get_all_rates(self):

        all_rates = {}

        query = {
            "epoch_state": {},
        }

        query_result = Terra.terra.wasm.contract_query(Terra.mmMarket, query)
        all_rates_uluna = Terra.terra.market.swap_rate(Coin('uluna', 1000000), 'uusd')

        MIR_pool_info, \
        SPEC_pool_info, \
        ANC_pool_info, \
        PSI_pool_info  \
                 = await asyncio.gather(
        self.get_pool_info(Terra.Mirror_MIR_UST_Pair),
        self.get_pool_info(Terra.Spectrum_SPEC_UST_Pair),
        self.get_pool_info(Terra.Terraswap_ANC_UST_Pair),
        self.get_pool_info(Terra.Nexus_PSI_UST_Pair),
        )

        all_rates['uluna'] = Dec(all_rates_uluna.amount)

        all_rates['aUST'] = Dec(query_result['exchange_rate']) * 1000000 

        all_rates['MIR'] = Dec(MIR_pool_info[1] / MIR_pool_info[0] * 1000000)
        all_rates['SPEC'] = Dec(SPEC_pool_info[1] / SPEC_pool_info[0] * 1000000)
        all_rates['ANC'] = Dec(ANC_pool_info[1] / ANC_pool_info[0] * 1000000)
        all_rates['PSI'] = Dec(PSI_pool_info[1] / PSI_pool_info[0] * 1000000)

        all_rates['MIR-TOKEN-PER-SHARE'] = Dec(MIR_pool_info[0] / MIR_pool_info[2])
        all_rates['MIR-UST-PER-SHARE'] = Dec(MIR_pool_info[1] / MIR_pool_info[2])
        
        all_rates['SPEC-TOKEN-PER-SHARE'] = Dec(SPEC_pool_info[0] / SPEC_pool_info[2])
        all_rates['SPEC-UST-PER-SHARE'] = Dec(SPEC_pool_info[1] / SPEC_pool_info[2])
        
        all_rates['ANC-TOKEN-PER-SHARE'] = Dec(ANC_pool_info[0] / ANC_pool_info[2])
        all_rates['ANC-UST-PER-SHARE'] = Dec(ANC_pool_info[1] / ANC_pool_info[2])

        all_rates['PSI-TOKEN-PER-SHARE'] = Dec(PSI_pool_info[0] / PSI_pool_info[2])
        all_rates['PSI-UST-PER-SHARE'] = Dec(PSI_pool_info[1] / PSI_pool_info[2])

        return all_rates

    async def get_fee_estimation(self):

        estimation = Terra.terra.treasury.tax_cap('uusd')
        fee = estimation.to_data().get('amount')
        return Dec(fee)

    async def get_pool_info(self, token_UST_pair_address:str):

        query = {
            "pool": {}
        }
        query_result = Terra.terra.wasm.contract_query(token_UST_pair_address, query)

        UST_in_pool = sum(Dec(asset['amount']) for asset in query_result['assets'] if asset['info'].get('token') is None)
        token_in_pool = sum(Dec(asset['amount']) for asset in query_result['assets'] if asset['info'].get('token') is not None)
        total_share = Dec(query_result['total_share'])

        return [token_in_pool, UST_in_pool, total_share]

    async def get_luna_col_multiplier(self):

        query = {
            "collateral_price": {
                "asset": "uluna"
            }
        }
        query_result = Terra.terra.wasm.contract_query(Terra.Collateral_Oracle, query)
        get_luna_col_multiplier = query_result['multiplier']
        return Dec(get_luna_col_multiplier)


    async def get_latest_block(self):
        result = Terra.terra.tendermint.block_info()
        height = result['block']['header']['height']
        return int(height)

    async def get_oracle_price_and_min_col_ratio(self, mAsset:str):
        oracle_price_and_min_col_ratio:list

        query_oracle_price_collateral = {
            "collateral_price": {
                "asset": mAsset
            },
        }
        query_oracle_price_mint = {
            "asset_config": {
                "asset_token": mAsset
            },
        }

        position_ids_result = Terra.terra.wasm.contract_query(Terra.Collateral_Oracle, query_oracle_price_collateral)
        min_col_ratio_result = Terra.terra.wasm.contract_query(Terra.Mint, query_oracle_price_mint)

        oracle_price_and_min_col_ratio = [Dec(position_ids_result['rate']), Dec(min_col_ratio_result['min_collateral_ratio'])]

        return oracle_price_and_min_col_ratio


    async def Mirror_get_position_info(self):
        Mirror_position_info:list
        Mirror_position_info = []
        reserve_UST = 0

        query_position_ids = {
            "positions": {
                "owner_addr": account_address
            },
        }

        position_ids_result = Terra.terra.wasm.contract_query(Terra.Mint, query_position_ids)
        luna_col_multiplier = await self.get_luna_col_multiplier()

        for position in position_ids_result['positions']:

            # There are currently three tokens that can be used as collateral Luna, UST, aUST, so we need to find out which one is used for each position_idx.
            position_idx = position['idx']
            
            # if denom exists, its means the collateral_token is either uusd or uluna
            if 'native_token' in position['collateral']['info']:
                collateral_token_denom = position['collateral']['info']['native_token']['denom']
            else:
                if position['collateral']['info']['token']['contract_addr'] == Terra.aTerra:
                    collateral_token_denom = 'aUST'
                else:
                    self.default_logger.warning(f'[Script] The collateral you have here is none of those: UST, aUST, LUNA. The bot cannot handle that.')
            
            # This value is returned from the blockchain in-kind.
            collateral_amount_in_kind = Dec(position['collateral']['amount'])

            # As the mAsset is valued in UST, we convert the colateral_amount also into UST here.
            if collateral_token_denom == 'aUST':
                collateral_amount_in_ust = collateral_amount_in_kind * self.all_rates['aUST'] / 1000000
            elif collateral_token_denom == 'uluna':
                collateral_amount_in_ust = collateral_amount_in_kind * self.all_rates['LUNAs'] / 1000000
            elif collateral_token_denom == 'uusd':
                collateral_amount_in_ust = collateral_amount_in_kind

            shorted_asset_qty = Dec(position['asset']['amount'])
            mAsset_address = position['asset']['info']['token']['contract_addr']

            if mAsset_address in Terra.rev_Contract_addresses.keys():
                mAsset_symbol = Terra.rev_Contract_addresses[mAsset_address]
            else:
                mAsset_symbol = 'Not in assets.Contact_addresses.py'

            oracle_price_and_min_col_ratio = await self.get_oracle_price_and_min_col_ratio(mAsset_address)
            oracle_price = oracle_price_and_min_col_ratio[0]
            shorted_asset_amount = oracle_price * shorted_asset_qty

            # If the collateral is provided in UST or aUST the min_col_ratio is as received form the query.
            # if the colalteral is Luna it is luna_col_multiplier (4/3) of the min_col_ratio
            if collateral_token_denom == 'uluna':
                min_col_ratio = oracle_price_and_min_col_ratio[1] * Dec(luna_col_multiplier)
            else:
                min_col_ratio = oracle_price_and_min_col_ratio[1]

            cur_col_ratio = collateral_amount_in_ust / shorted_asset_amount
            lower_trigger_ratio = min_col_ratio + Dec(config.Mirror_lower_distance)
            target_ratio = min_col_ratio + Dec(config.Mirror_target_distance)
            upper_trigger_ratio = min_col_ratio + Dec(config.Mirror_upper_distance)

            collateral_loss_to_liq = -(shorted_asset_amount * min_col_ratio / collateral_amount_in_ust) + 1
            shorted_mAsset_gain_to_liq = (collateral_amount_in_ust / min_col_ratio / shorted_asset_amount) - 1

            distance_to_min_col = cur_col_ratio - min_col_ratio

            reserve_UST += cur_col_ratio * 1.05 * shorted_asset_amount

            if cur_col_ratio < lower_trigger_ratio \
                    and config.Mirror_enable_deposit_collateral:
                action_to_be_executed = 'deposit'
                # Calculate how much in-kind to withdraw to return to the desired ratio, even if the collaterial is not in UST
                # v This is how much collateral is already in
                amount_to_execute_in_ust = target_ratio * shorted_asset_amount - collateral_amount_in_ust
                # ^ This is how much absolut collateral in UST is required to get the desired target_ratio
                # Quick rule of three
                amount_to_execute_in_kind = (
                    collateral_amount_in_kind / collateral_amount_in_ust) * amount_to_execute_in_ust

            elif cur_col_ratio > upper_trigger_ratio \
                    and config.Mirror_enable_withdraw_collateral:
                action_to_be_executed = 'withdraw'
                # Calculate how much in-kind to withdraw to return to the desired ratio, even if the collaterial is not in UST
                # v This is how much collateral is already in
                amount_to_execute_in_ust = collateral_amount_in_ust - target_ratio * shorted_asset_amount
                # ^ This is how much absolut collateral in UST is required to get the desired target_ratio
                # Quick rule of three
                amount_to_execute_in_kind = (collateral_amount_in_kind / collateral_amount_in_ust) * amount_to_execute_in_ust

            else:
                action_to_be_executed = 'none'
                amount_to_execute_in_kind = 0
                amount_to_execute_in_ust = 0

            Mirror_position_info.append({
                'position_idx': position_idx,
                'mAsset_symbol': mAsset_symbol,
                'mAsset_address': mAsset_address,
                'collateral_token_denom': collateral_token_denom,
                'collateral_amount_in_kind': collateral_amount_in_kind,
                'collateral_amount_in_ust': collateral_amount_in_ust,
                'shorted_asset_qty': shorted_asset_qty,
                'oracle_price': oracle_price,
                'shorted_asset_amount': shorted_asset_amount,
                'min_col_ratio': min_col_ratio,
                'cur_col_ratio': cur_col_ratio,
                'lower_trigger_ratio': lower_trigger_ratio,
                'target_ratio': target_ratio,
                'upper_trigger_ratio': upper_trigger_ratio,
                'collateral_loss_to_liq' : collateral_loss_to_liq,
                'shorted_mAsset_gain_to_liq': shorted_mAsset_gain_to_liq,
                'action_to_be_executed': action_to_be_executed,
                'amount_to_execute_in_kind': amount_to_execute_in_kind,
                'amount_to_execute_in_ust': amount_to_execute_in_ust,
                'distance_to_min_col': distance_to_min_col,
                'reserve_UST': reserve_UST,
            })

        # Sort positions by distance_to_min_col (lowest first)
        def sort_by_distance(elem):
            return elem['distance_to_min_col']

        # Sort positions by action (withdrawals first)
        def sort_by_action(elem):
            return elem['action_to_be_executed']

        Mirror_position_info.sort(key=sort_by_distance)
        Mirror_position_info.sort(key=sort_by_action, reverse=True)

        return Mirror_position_info


    def get_claimable_MIR(self):

        claimable = 0

        query = {
            "reward_info": {
                "staker_addr": account_address
            },
        }

        query_result = Terra.terra.wasm.contract_query(Terra.MirrorStaking, query)

        # Sum up all claimable rewards for this account_address
        claimable = sum(Dec(reward['pending_reward']) for reward in query_result['reward_infos'])

        return Dec(claimable)


    async def get_claimable_SPEC(self):
        claimable_SPEC_list:list
        claimable_mirrorFarm = 0
        claimable_anchorFarm = 0
        claimable_specFarm = 0
        claimable_pylonFarm = 0

        latest_block = await self.get_latest_block()

        Mirror_SPEC_query = {
            "reward_info": {
                "staker_addr": account_address,
                "height": latest_block
            },
        }

        Anchor_SPEC_query = {
            "reward_info": {
                "staker_addr": account_address,
                "height": latest_block
            },
        }

        Spectrum_SPEC_query = {
            "reward_info": {
                "staker_addr": account_address,
                "height": latest_block
            },
        }

        Pylon_SPEC_query = {
            "reward_info": {
                "staker_addr": account_address,
                "height": latest_block
            },
        }
        
        try:
            query_result_mirrorFarm = Terra.terra.wasm.contract_query(Terra.mirrorFarm, Mirror_SPEC_query)
            query_result_anchorFarm = Terra.terra.wasm.contract_query(Terra.anchorFarm, Anchor_SPEC_query)
            query_result_specFarm = Terra.terra.wasm.contract_query(Terra.specFarm, Spectrum_SPEC_query)
            query_result_pylonFarm = Terra.terra.wasm.contract_query(Terra.pylonFarm, Pylon_SPEC_query)

            claimable_mirrorFarm = Dec(sum(Dec(reward['pending_spec_reward']) for reward in query_result_mirrorFarm['reward_infos']))
            claimable_anchorFarm = Dec(sum(Dec(reward['pending_spec_reward']) for reward in query_result_anchorFarm['reward_infos']))
            claimable_specFarm = Dec(sum(Dec(reward['pending_spec_reward']) for reward in query_result_specFarm['reward_infos']))
            claimable_pylonFarm = Dec(sum(Dec(reward['pending_spec_reward']) for reward in query_result_pylonFarm['reward_infos']))

            claimable_SPEC_list = [
                +claimable_mirrorFarm \
                +claimable_anchorFarm \
                +claimable_specFarm \
                +claimable_pylonFarm,
                claimable_mirrorFarm >0,
                claimable_anchorFarm >0,
                claimable_specFarm >0,
                claimable_pylonFarm >0,
            ]
            return claimable_SPEC_list

        except LCDResponseError as err:
            if err.response.status == 520:
                claimable_SPEC_list = [0, False, False, False, False]


    async def get_claimable_ANC(self, retry=0):

        try:

            latest_block = await self.get_latest_block()

            query = {
                "borrower_info": {
                    "borrower": account_address,
                    "block_height": latest_block
                }
            }

            query_result = Terra.terra.wasm.contract_query(Terra.mmMarket, query)

            claimable = query_result['pending_rewards']

            return Dec(claimable)

        except LCDResponseError as err:
            if retry < 2:
                retry += 1
                sleep(5)
                self.get_claimable_ANC(retry)
            else:
                raise err

    async def get_claimable_PSI(self):
        claimable = 0

        query = {"accrued_rewards":
            {
                "address":account_address
            }
        }

        query_result = Terra.terra.wasm.contract_query(Terra.NexusnETHrewards, query)

        # Sum up all claimable rewards for this account_address
        claimable = query_result['rewards']

        return Dec(claimable)

    def Mirror_get_claimable_UST(self, Mirror_position_info:list, retry=0):

        claimable = 0

        # Input: Mirror_position_info
        # Output: Returns the quantity of UST that can be claimed
        # https://docs.mirror.finance/contracts/lock#positionlockinfo

        for position in Mirror_position_info:

            query = {
                "position_lock_info": {
                    "position_idx": position['position_idx']
                }
            }

            try:
                query_result = Terra.terra.wasm.contract_query(Terra.Lock, query)
                locked_amount = Dec(query_result['locked_amount'])
                unlock_time = Dec(query_result['unlock_time'])
                now_time = Dec(datetime.now().timestamp())
                if unlock_time < now_time:
                    claimable += locked_amount
            
            except LCDResponseError as err:
                # Status code 500 means, that there is no unclaimed UST. If so, this exception can be ignored
                if err.response.status == 500:
                    pass
                elif retry < 2:
                    retry += 1
                    sleep(5)
                    self.Mirror_get_claimable_UST(Mirror_position_info, retry)
                else:
                    raise err

        return Dec(claimable)


    def simulate_Token_Swap(self, token_amount:Dec, token_UST_pair_address:str, token_address:str):

        query = {
            "simulation": {
                "offer_asset": {
                    "amount": str(int(token_amount)),
                    "info": {
                        "token": {
                            "contract_addr": token_address
                        }
                    }
                }
            }
        }

        try:
            query_result = Terra.terra.wasm.contract_query(token_UST_pair_address, query)
            UST_return = query_result['return_amount']

        except LCDResponseError as err:
            if err.response.status == 520:
                UST_return = 0
                
        return Dec(UST_return)

    def get_available_LP_token_for_withdrawal(self, token_farm_address:str, token_address:str):
       
        LP_token_available = 0

        query = {
            "reward_info": {
                "staker_addr": account_address, 
            }
        }
        query_result = Terra.terra.wasm.contract_query(token_farm_address, query)

        if query_result != []:
            LP_token_available = sum(Dec(reward_info['bond_amount']) for reward_info in query_result['reward_infos'] if reward_info['asset_token'] == token_address)

        return Dec(LP_token_available)

    async def Anchor_get_max_ltv_ratio(self):

        query = {
            "whitelist": {},
        }
        query_result = Terra.terra.wasm.contract_query(Terra.mmOverseer, query)

        return dict((elem['symbol'], Dec(elem['max_ltv'])) for elem in query_result['elems'])


    async def Anchor_get_borrow_info(self):
        Anchor_debt_info:dict

        query_msg_borrow_limit = {
            "borrow_limit": {
                "borrower": account_address
            },
        }           
        query_msg_collateral = {
            "collaterals": {
                "borrower": account_address
            },
        }
        query_msg_borrower_info = {
            "borrower_info": {
                "borrower": account_address
            },
        }

        Anchor_get_max_ltv_ratio = await self.Anchor_get_max_ltv_ratio()
        borrow_limit_result = Terra.terra.wasm.contract_query(Terra.mmOverseer, query_msg_borrow_limit)
        query_msg_collateral_result = Terra.terra.wasm.contract_query(Terra.mmOverseer, query_msg_collateral)
        query_msg_borrower_info_result = Terra.terra.wasm.contract_query(Terra.mmMarket, query_msg_borrower_info)

        max_ltv_ratio = Anchor_get_max_ltv_ratio['BETH']
        borrow_limit = Dec(borrow_limit_result['borrow_limit'])

        # Check if you actually have some collateral in Anchor
        if borrow_limit > 0:

            loan_amount = Dec(query_msg_borrower_info_result['loan_amount'])

            collateral_dict = dict((collateral[0], Dec(collateral[1])) for collateral in query_msg_collateral_result['collaterals'])

            if collateral_dict.get(Terra.bETH_token) is not None:
                amount_bETH_collateral = collateral_dict[Terra.bETH_token]
            else:
                amount_bETH_collateral = 0

            if collateral_dict.get(Terra.bLuna_token) is not None:
                amount_bLuna_collateral = collateral_dict[Terra.bLuna_token]
            else:
                amount_bLuna_collateral = 0

            total_collateral_value = borrow_limit / max_ltv_ratio
            cur_col_ratio = loan_amount / borrow_limit * max_ltv_ratio
            lower_trigger_ratio = max_ltv_ratio + Dec(config.Anchor_lower_distance)
            upper_trigger_ratio = max_ltv_ratio + Dec(config.Anchor_upper_distance)
            distance_to_max_ltv = cur_col_ratio - max_ltv_ratio

            collateral_loss_to_liq = -(loan_amount / max_ltv_ratio / total_collateral_value) + 1

            if cur_col_ratio > lower_trigger_ratio and config.Anchor_enable_auto_repay_of_debt:
                action_to_be_executed = 'repay'
                # Calculate how much aUST to deposite to return to the desired ratio
                amount_to_execute_in_ust = loan_amount - (borrow_limit * (max_ltv_ratio + Dec(config.Anchor_target_distance)) / max_ltv_ratio)
            elif cur_col_ratio < upper_trigger_ratio and config.Anchor_enable_auto_borrow_UST:
                action_to_be_executed = 'borrow'
                # Calculate how much aUST to withdraw to return to the desired ratio
                amount_to_execute_in_ust = (borrow_limit * (max_ltv_ratio + Dec(config.Anchor_target_distance)) / max_ltv_ratio) - loan_amount
            else:
                action_to_be_executed = 'none'
                amount_to_execute_in_ust = 0

            Anchor_debt_info = {
                'loan_amount': loan_amount,
                'amount_bETH_collateral': amount_bETH_collateral,
                'amount_bLuna_collateral': amount_bLuna_collateral,
                'total_collateral_value': total_collateral_value,
                'borrow_limit': borrow_limit,
                'cur_col_ratio': cur_col_ratio,
                'lower_trigger_ratio': lower_trigger_ratio,
                'upper_trigger_ratio': upper_trigger_ratio,
                'distance_to_max_ltv': distance_to_max_ltv,
                'collateral_loss_to_liq':collateral_loss_to_liq,
                'action_to_be_executed': action_to_be_executed,
                'amount_to_execute_in_ust': amount_to_execute_in_ust
            }
            
        else:
            Anchor_debt_info = {
                'loan_amount': 0,
                'amount_bETH_collateral': 0,
                'amount_bLuna_collateral': 0,
                'total_collateral_value': 0,
                'borrow_limit': borrow_limit,
                'cur_col_ratio': 0,
                'lower_trigger_ratio': 0,
                'upper_trigger_ratio': 0,
                'distance_to_max_ltv': 0,
                'collateral_loss_to_liq':0,
                'action_to_be_executed': 'none',
                'amount_to_execute_in_ust': 0
            }

        return Anchor_debt_info

    def get_status_of_tx(self, tx_hash, retry=0):

        if search("[A-F0-9]{64}", tx_hash) is None:
            return tx_hash

        if config.Disable_all_transaction_defs:
            if config.Return_failed_tx:
                return "Dummy reason for failed tx"
            else:
                return True

        sleep(5)

        try:
            status = Terra.terra.tx.tx_info(tx_hash)
            if status.code is None:
                # Transaction successful
                return True
            else:
                # Transaction failed
                return status.rawlog
        except LCDResponseError as err:
            if err.response.status == 404 and retry < 3:
                retry +=1
                sleep(5)
                self.get_status_of_tx(tx_hash, retry)
            else:
                return f'Transaction hash could not be found even after multiple retries.'

    def market_hours(self, retry=0):

        # Oracle query mAPPL
        # https://fcd.terra.dev/wasm/contracts/terra1t6xe0txzywdg85n6k8c960cuwgh6l8esw6lau9/store?query_msg={"price":{"base_asset":"terra1vxtwu4ehgzz77mnfwrntyrmgl64qjs75mpwqaz","quote_asset":"uusd"}}
        # 
        # Oracle query mBTC
        # https://fcd.terra.dev/wasm/contracts/terra1t6xe0txzywdg85n6k8c960cuwgh6l8esw6lau9/store?query_msg={"price":{"base_asset":"terra1rhhvx8nzfrx5fufkuft06q5marfkucdqwq5sjw","quote_asset":"uusd"}}
        
        # If the query for mAAPL returns a last_updated_base that is older than 2min, it will assume the market is closed        
        # https://www.nasdaq.com/stock-market-trading-hours-for-nasdaq

        try:
            query = {
                "price": {
                    "base_asset": Terra.mAAPL_token,
                    "quote_asset":"uusd"
                }
            }
            query_result = Terra.terra.wasm.contract_query(Terra.Oracle, query)

            unix_last_price_update = query_result['last_updated_base']
            unix_now = mktime(datetime.now().timetuple())

            time_difference = unix_now - unix_last_price_update

            if time_difference < 120: # 2 min = 60*2 = 120 seconds
                return True
            else:
                return False
        except LCDResponseError as err:
            if retry < 2:
                retry += 1
                sleep(5)
                self.market_hours(retry)
            else:
                raise err


    def get_native_balance(self, denom:str):
        balance_native = Terra.terra.bank.balance(address=account_address)
        
        return sum(Dec(item['amount']) for item in balance_native[0].to_data() if item['denom'] == denom)

    async def get_non_native_balance(self, token_address): 
        query = {
            "balance": {
                "address": account_address
            }
        }
        query_result = Terra.terra.wasm.contract_query(token_address, query)

        return Dec(query_result['balance'])
    

    async def get_wallet_balances(self):

        wallet_balances = {}

        balance_native = Terra.terra.bank.balance(address=account_address)

        wallet_balances['aUST'], \
        wallet_balances['MIR'], \
        wallet_balances['SPEC'], \
        wallet_balances['ANC'], \
        wallet_balances['PSI'] \
            = await asyncio.gather(
            self.get_non_native_balance(Terra.aUST_token),
            self.get_non_native_balance(Terra.MIR_token),
            self.get_non_native_balance(Terra.SPEC_token),
            self.get_non_native_balance(Terra.ANC_token),
            self.get_non_native_balance(Terra.PSI_token)
        )

        for i in balance_native[0].to_data():
            wallet_balances[i['denom']] = Dec(i['amount'])

        return wallet_balances