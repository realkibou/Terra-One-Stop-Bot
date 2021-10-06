#!/usr/bin/python3

# Terra SDK
from terra_sdk.core.coins import Coins
from terra_sdk.core.coins import Coin
from terra_sdk.core.auth import StdFee
from terra_sdk.core.wasm import MsgExecuteContract

# Other assets
from assets.Terra import Terra
from assets.Queries import Queries
import B_Config as config
from assets.Logging import Logger

class Transaction:

    def __init__(self):
        self.fee_estimation = Queries().get_fee_estimation()
        # Todo implement this
        self.low_fee = str(int(config.Fee_multiplier_for_cheap_transactions * self.fee_estimation)) + "uusd"
        self.std_fee = str(int(self.fee_estimation)) + "uusd"
        self.high_fee = str(int(config.Fee_multiplier_for_expensive_transactions * self.fee_estimation)) + "uusd"
        self.default_logger = Logger().default_logger

    # For debugging only
    if config.Disable_all_transaction_defs:
        if config.Return_failed_tx:
            def Mirror_deposit_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return Terra().failed_tx_hash
            def Anchor_borrow_more_UST(self, amount): return Terra().failed_tx_hash
            def Anchor_deposit_UST_for_Earn(self, amount): return Terra().failed_tx_hash
            def Anchor_repay_debt_UST(self, amount): return Terra().failed_tx_hash
            def Anchor_withdraw_UST_from_Earn(self, amount, denom): return Terra().failed_tx_hash
            def claim_ANC(self): return Terra().failed_tx_hash
            def claim_MIR(self): return Terra().failed_tx_hash
            def claim_SPEC(self, claimable_SPEC): return Terra().failed_tx_hash
            def Mirror_claim_unlocked_UST(self, Mirror_position_info): return Terra().failed_tx_hash
            def Mirror_withdraw_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return Terra().failed_tx_hash
            def sell_ANC(self, amount): return Terra().failed_tx_hash
            def sell_MIR(self, amount): return Terra().failed_tx_hash
            def sell_SPEC(self, amount): return Terra().failed_tx_hash
            def Mirror_deposit_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return Terra().failed_tx_hash
        else:
            def Mirror_deposit_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return Terra().success_tx_hash
            def Anchor_borrow_more_UST(self, amount): return Terra().success_tx_hash
            def Anchor_deposit_UST_for_Earn(self, amount): return Terra().success_tx_hash
            def Anchor_repay_debt_UST(self, amount): return Terra().success_tx_hash
            def Anchor_withdraw_UST_from_Earn(self, amount, denom): return Terra().success_tx_hash
            def claim_ANC(self): return Terra().success_tx_hash
            def claim_MIR(self): return Terra().success_tx_hash
            def claim_SPEC(self, claimable_SPEC): return Terra().success_tx_hash
            def Mirror_claim_unlocked_UST(self, Mirror_position_info): return Terra().success_tx_hash
            def Mirror_withdraw_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return Terra().success_tx_hash
            def sell_ANC(self, amount): return Terra().success_tx_hash
            def sell_MIR(self, amount): return Terra().success_tx_hash
            def sell_SPEC(self, amount): return Terra().success_tx_hash
            def Mirror_deposit_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return Terra().success_tx_hash

    else:
        def Mirror_deposit_collateral_for_position(self, idx, collateral_amount_in_kind, denom):

            amount = int(collateral_amount_in_kind*1e6)

            # Depending on the denom, hence the token that was used for the collateral we need to change this tx's details
            if denom == 'aUST':

                contract=Terra().aTerra
                execute_msg={
                    "send": {
                        "amount": str(amount),
                        "contract": Terra().Mint,
                        "msg": {
                            "deposit": {
                                "position_idx": idx,
                                "collateral": {
                                    "amount": str(amount),
                                    "info": {
                                        "token": {
                                            "contract_addr": Terra().aTerra,
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                coins=Coins()

            else:
                # Luna and UST are natively supported
                coin = Coin(denom, int(collateral_amount_in_kind*1e6)).to_data()
                coins = Coins.from_data([coin])

                contract = Terra().Mint
                execute_msg={
                    "deposit": {
                        "position_idx": idx,
                        "collateral": {
                            "amount": str(amount),
                            "info": {
                                "native_token": {
                                    "denom": denom
                                }
                            }
                        }
                    }
                },

            fee = self.low_fee
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def Mirror_withdraw_collateral_for_position(self, idx, collateral_amount_in_kind, denom):

            amount = int(collateral_amount_in_kind*1e6)

            # Depending on the denom, hence the token that was used for the collateral we need to change this tx's details
            if denom == 'aUST':
                # https://finder.terra.money/tequila-0004/tx/10C1B6310DA5B16F5EE96F3535B99C9CD7DC5D696054D547C32A54F2317E930B

                contract=Terra().aTerra
                execute_msg={
                    "withdraw": {
                        "position_idx": idx,
                        "collateral": {
                            "amount": str(amount),
                            "info": {
                                "token": {
                                    "contract_addr": Terra().aTerra
                                }
                            }
                        }
                    }
                }
                coins=Coins()

            else:
                coin = Coin('uusd', int(collateral_amount_in_kind*1e6)).to_data()
                coins = Coins.from_data([coin])

                contract=Terra().Mint
                execute_msg={
                        "withdraw": {
                            "position_idx": idx,
                            "collateral": {
                                "amount": str(amount),
                                "info": {
                                    "native_token": {
                                        "denom": "uusd"
                                    }
                                }
                            }
                        }
                    },

            fee = self.low_fee
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def Mirror_claim_unlocked_UST(self, Mirror_position_info):

            def position_idxs_to_be_claimed():
                position_idxs_to_be_claimed = []
                for position in Mirror_position_info:
                    position_idxs_to_be_claimed.append(position['position_idx'])
                return position_idxs_to_be_claimed

            contract=Terra().Lock
            execute_msg={
                "unlock_position_funds": {
                    "positions_idx": position_idxs_to_be_claimed()
                }
            }
            coins=Coins()

            fee = self.low_fee
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def claim_MIR(self):

            contract=Terra().Staking
            execute_msg={
                "withdraw": {}
            }
            coins = Coins()

            fee = self.low_fee
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def claim_SPEC(self, claimable_SPEC):
                
            # claimable_SPEC contains from index 1 True/False if there is any Spec to claim:
            # claimable_mirrorFarm
            # claimable_anchorFarm
            # claimable_specFarm
            # claimable_pylonFarm

            send = []

            send.append(
                MsgExecuteContract( 
                sender=Terra().wallet.key.acc_address,
                contract=Terra().specgov,
                execute_msg={
                    "mint": {}
                }
            ))

            if claimable_SPEC[1] == True:
                send.append(
                    MsgExecuteContract( # Withdraw SPEC from your mirrorFarm
                    sender=Terra().wallet.key.acc_address,
                    contract=Terra().mirrorFarm,
                    execute_msg={
                        "withdraw": {}
                    }
                ))
            
            if claimable_SPEC[2] == True:
                send.append(
                    MsgExecuteContract( # Withdraw SPEC from your anchorFarm
                    sender=Terra().wallet.key.acc_address,
                    contract=Terra().anchorFarm,
                    execute_msg={
                        "withdraw": {}
                    }
                ))
            
            if claimable_SPEC[3] == True:
                send.append(
                    MsgExecuteContract( # Withdraw SPEC from your specFarm
                    sender=Terra().wallet.key.acc_address,
                    contract=Terra().specFarm,
                    execute_msg={
                        "withdraw": {}
                    }
                ))

            if claimable_SPEC[4] == True:
                send.append(
                    MsgExecuteContract( # Withdraw SPEC from your pylonfarm
                    sender=Terra().wallet.key.acc_address,
                    contract=Terra().pylonFarm,
                    execute_msg={
                        "withdraw": {}
                    }
                ))
            
            fee = StdFee(3000000, self.std_fee)
            sendtx = Terra().wallet.create_and_sign_tx(send, fee)
            result = Terra().terra.tx.broadcast(sendtx)

            return result.txhash


        def claim_ANC(self):

            contract=Terra().mmMarket
            execute_msg={
                "claim_rewards": {}
            }
            coins=Coins()

            fee = self.low_fee
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def sell_MIR(self, amount):

            # https://docs.terraswap.io/docs/howto/swap/

            contract=Terra().MIR_token
            execute_msg={
                "send": {
                    "contract": Terra().Terraswap_MIR_UST_Pair,
                    "amount": str(int(amount*1e6)),
                    "msg": "eyJzd2FwIjp7fX0="
                }
            }
            coins=Coins()

            fee = self.low_fee
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def sell_SPEC(self, amount):
            # https://docs.terraswap.io/docs/howto/swap/

            contract=Terra().SPEC_token
            execute_msg={
                "send": {
                    "contract": Terra().Spectrum_SPEC_UST_Pair,
                    "amount": str(int(amount*1e6)),
                    "msg": "eyJzd2FwIjp7fX0="
                }
            }

            coins=Coins()

            fee = self.low_fee
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def sell_ANC(self, amount):
            # https://docs.terraswap.io/docs/howto/swap/

            contract=Terra().ANC_token
            execute_msg={
                "send": {
                    "contract": Terra().Terraswap_ANC_UST_Pair,
                    "amount": str(int(amount*1e6)),
                    "msg": "eyJzd2FwIjp7fX0="
                }
            }

            coins=Coins()

            fee = self.low_fee
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def Anchor_deposit_UST_for_Earn(self, amount):
            amount = int(amount * 1e6)

            # Depoit a bit less, to have some UST for tx fees
            coin = Coin('uusd', amount - self.fee_estimation * config.Safety_multiple_on_transaction_fees).to_data()
            coins = Coins.from_data([coin])

            contract=Terra().mmMarket
            execute_msg={
                "deposit_stable": {}
            },

            fee = self.high_fee
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def Anchor_withdraw_UST_from_Earn(self, amount, denom):

            # Convert amount UST into aUST for withdrawl and add a bit more for fees
            if denom == 'UST':
                amount = amount / Queries().get_aUST_rate()            

            amount = int(amount * 1e6)

            contract=Terra().aTerra
            execute_msg={
                    "send": {
                        "contract": Terra().mmMarket,
                        "amount": str(amount),
                        "msg": "eyJyZWRlZW1fc3RhYmxlIjp7fX0="}
            }
            coins = Coins()

            fee = self.low_fee
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def Anchor_repay_debt_UST(self, amount):
            amount = int(amount * 1000000)

            # Deduct the fee incl safety so there is still some UST left
            coin = Coin('uusd', amount - self.fee_estimation * config.Safety_multiple_on_transaction_fees).to_data()
            coins = Coins.from_data([coin])

            contract=Terra().mmMarket
            execute_msg={
                "repay_stable": {}
            }

            fee = self.high_fee
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash


        def Anchor_borrow_more_UST(self, amount):

            amount = int((amount * 1e6) + self.fee_estimation * config.Safety_multiple_on_transaction_fees)

            contract=Terra().mmMarket
            execute_msg={
                "borrow_stable": {
                    "borrow_amount": f'{amount}'
                }
            }
            
            coins = Coins()

            fee = self.high_fee
            txhash = self.execute_transaction(contract, execute_msg, coins, fee)
            return txhash

        def execute_transaction(self, contract, execute_msg, coins, fee):

            try:
                message = MsgExecuteContract(
                    sender=Terra().wallet.key.acc_address,
                    contract=contract,
                    execute_msg=execute_msg,
                    coins=coins,
                )

                transaction = Terra().wallet.create_and_sign_tx(
                    msgs=[message], 
                    fee=StdFee(1000000, fee),
                    memo='One-Stop-Bot',
                    )

                result = Terra().terra.tx.broadcast(transaction)
                return result.txhash

            except Exception as err:
                self.default_logger.warning(err)