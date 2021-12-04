#!/usr/bin/python3

# Terra SDK
import asyncio
from terra_sdk.core.coins import Coins
from terra_sdk.core.coins import Coin
from terra_sdk.core.wasm import MsgExecuteContract
from terra_sdk.core.numeric import Dec
from terra_sdk.exceptions import LCDResponseError

# Other assets
from assets.Terra import Terra
from assets.Queries import Queries
from assets.Logging import Logger
import B_Config as config
import base64, json

Queries_class = Queries()
account_address = Terra.account_address
fee_estimation = Dec(asyncio.run(Queries_class.get_fee_estimation()))

class Transaction:
    if config.Debug_mode: print(f'Transactions Class loaded.')
    default_logger = Logger().default_logger

    # For debugging only
    if config.Disable_all_transaction_defs:
        if config.Return_failed_tx:
            def Mirror_deposit_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return Terra.failed_tx_hash
            def Anchor_borrow_more_UST(self, amount): return Terra.failed_tx_hash
            def Anchor_deposit_UST_for_Earn(self, amount): return Terra.failed_tx_hash
            def Anchor_repay_debt_UST(self, amount): return Terra.failed_tx_hash
            def Anchor_withdraw_UST_from_Earn(self, amount, denom): return Terra.failed_tx_hash
            def claim_ANC(self): return Terra.failed_tx_hash
            def claim_MIR(self): return Terra.failed_tx_hash
            def claim_SPEC(self, claimable_SPEC_list): return Terra.failed_tx_hash
            def claim_PSI(self): return Terra.failed_tx_hash
            def Mirror_claim_unlocked_UST(self, Mirror_position_info): return Terra.failed_tx_hash
            def Mirror_withdraw_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return Terra.failed_tx_hash
            def sell_ANC(self, amount): return Terra.failed_tx_hash
            def sell_MIR(self, amount): return Terra.failed_tx_hash
            def sell_SPEC(self, amount): return Terra.failed_tx_hash
            def sell_PSI(self, amount): return Terra.failed_tx_hash
            def deposit_ANC_in_pool(self, amount_token, amount_UST): return Terra.failed_tx_hash
            def deposit_MIR_in_pool(self, amount_token, amount_UST): return Terra.failed_tx_hash
            def deposit_SPEC_in_pool(self, amount_token, amount_UST): return Terra.failed_tx_hash
            def withdraw_MIR_from_pool(self, amount_lp_token): return Terra.failed_tx_hash
            def withdraw_SPEC_from_pool(self, amount_lp_token): return Terra.failed_tx_hash
            def withdraw_ANC_from_pool(self, amount_lp_token): return Terra.failed_tx_hash

        else:
            def Mirror_deposit_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return Terra.success_tx_hash
            def Anchor_borrow_more_UST(self, amount): return Terra.success_tx_hash
            def Anchor_deposit_UST_for_Earn(self, amount): return Terra.success_tx_hash
            def Anchor_repay_debt_UST(self, amount): return Terra.success_tx_hash
            def Anchor_withdraw_UST_from_Earn(self, amount, denom): return Terra.success_tx_hash
            def claim_ANC(self): return Terra.success_tx_hash
            def claim_MIR(self): return Terra.success_tx_hash
            def claim_SPEC(self, claimable_SPEC_list): return Terra.success_tx_hash
            def claim_PSI(self): return Terra.success_tx_hash
            def Mirror_claim_unlocked_UST(self, Mirror_position_info): return Terra.success_tx_hash
            def Mirror_withdraw_collateral_for_position(self, idx, collateral_amount_in_kind, denom): return Terra.success_tx_hash
            def sell_ANC(self, amount): return Terra.success_tx_hash
            def sell_MIR(self, amount): return Terra.success_tx_hash
            def sell_SPEC(self, amount): return Terra.success_tx_hash
            def sell_PSI(self, amount): return Terra.success_tx_hash
            def deposit_ANC_in_pool(self, amount_token, amount_UST): return Terra.success_tx_hash
            def deposit_MIR_in_pool(self, amount_token, amount_UST): return Terra.success_tx_hash
            def deposit_SPEC_in_pool(self, amount_token, amount_UST): return Terra.success_tx_hash
            def withdraw_MIR_from_pool(self, amount_lp_token): return Terra.success_tx_hash
            def withdraw_SPEC_from_pool(self, amount_lp_token): return Terra.success_tx_hash
            def withdraw_ANC_from_pool(self, amount_lp_token): return Terra.success_tx_hash

    else:
        def Mirror_deposit_collateral_for_position(self, idx:str, collateral_amount_in_kind:Dec, denom:str):
            collateral_amount_in_kind = int(collateral_amount_in_kind)
            # Depending on the denom, hence the token that was used for the collateral we need to change this tx's details
            if denom == 'aUST':

                contract=Terra.aTerra
                msg = {
                    "deposit": {
                        "position_idx": idx,
                        "collateral": {
                            "amount": str(collateral_amount_in_kind),
                            "info": {
                                "token": {
                                    "contract_addr": Terra.aTerra,
                                }
                            }
                        }
                    }
                }
                
                execute_msg = {
                    "send": {
                        "amount": str(collateral_amount_in_kind),
                        "contract": Terra.Mint,
                        "msg": base64.b64encode(bytes(json.dumps(msg), "ascii")).decode(),
                    }
                }
                coins=Coins()

            else:
                # Luna and UST are natively supported
                coins = Coins([Coin(denom, collateral_amount_in_kind)])

                contract = Terra.Mint
                execute_msg={
                    "deposit": {
                        "position_idx": idx,
                        "collateral": {
                            "amount": str(collateral_amount_in_kind),
                            "info": {
                                "native_token": {
                                    "denom": denom
                                }
                            }
                        }
                    }
                }

            txhash = self.execute_transaction(contract, execute_msg, coins)
            return txhash


        def Mirror_withdraw_collateral_for_position(self, idx:str, collateral_amount_in_kind:Dec, denom:str):
            collateral_amount_in_kind = int(collateral_amount_in_kind)
            # Depending on the denom, hence the token that was used for the collateral we need to change this tx's details
            if denom == 'aUST':
                # https://finder.terra.money/tequila-0004/tx/10C1B6310DA5B16F5EE96F3535B99C9CD7DC5D696054D547C32A54F2317E930B

                contract=Terra.Mint
                execute_msg={
                    "withdraw": {
                        "collateral": {
                            "info": {
                                "token": {
                                    "contract_addr": Terra.aTerra
                                }
                            },
                            "amount": str(collateral_amount_in_kind),
                        },
                    "position_idx": idx,
                    }
                }
                coins=Coins()

            else:
                coins = Coins([Coin('uusd', collateral_amount_in_kind)])

                contract=Terra.Mint
                execute_msg={
                        "withdraw": {
                            "collateral": {
                                "info": {
                                    "native_token": {
                                        "denom": "uusd"
                                    }
                                },
                                "amount": str(collateral_amount_in_kind),
                            },
                        "position_idx": idx,
                        }
                    }

            txhash = self.execute_transaction(contract, execute_msg, coins)
            return txhash


        def Mirror_claim_unlocked_UST(self, Mirror_position_info:dict):

            contract=Terra.Lock
            execute_msg={
                "unlock_position_funds": {
                    "positions_idx": [position['position_idx'] for position in Mirror_position_info]
                }
            }
            coins=Coins()

            txhash = self.execute_transaction(contract, execute_msg, coins)
            return txhash


        def claim_MIR(self):

            contract=Terra.MirrorStaking
            execute_msg={
                "withdraw": {}
            }
            coins = Coins()

            txhash = self.execute_transaction(contract, execute_msg, coins)
            return txhash


        def claim_SPEC(self, claimable_SPEC_list:list):
                
            # claimable_SPEC_list contains from index 1 True/False if there is any Spec to claim:
            # claimable_mirrorFarm
            # claimable_anchorFarm
            # claimable_SPEC_listFarm
            # claimable_pylonFarm

            message = []

            message.append(
                MsgExecuteContract( 
                sender=account_address,
                contract=Terra.specgov,
                execute_msg={
                    "mint": {}
                }
            ))

            if claimable_SPEC_list[1] == True:
                message.append(
                    MsgExecuteContract( # Withdraw SPEC from your mirrorFarm
                    sender=account_address,
                    contract=Terra.mirrorFarm,
                    execute_msg={
                        "withdraw": {}
                    }
                ))
            
            if claimable_SPEC_list[2] == True:
                message.append(
                    MsgExecuteContract( # Withdraw SPEC from your anchorFarm
                    sender=account_address,
                    contract=Terra.anchorFarm,
                    execute_msg={
                        "withdraw": {}
                    }
                ))
            
            if claimable_SPEC_list[3] == True:
                message.append(
                    MsgExecuteContract( # Withdraw SPEC from your specFarm
                    sender=account_address,
                    contract=Terra.specFarm,
                    execute_msg={
                        "withdraw": {}
                    }
                ))

            if claimable_SPEC_list[4] == True:
                message.append(
                    MsgExecuteContract( # Withdraw SPEC from your pylonfarm
                    sender=account_address,
                    contract=Terra.pylonFarm,
                    execute_msg={
                        "withdraw": {}
                    }
                ))

            sendtx = Terra.wallet.create_and_sign_tx(message, memo='Terra One-Stop-Bot by realKibou')
            result = Terra.terra.tx.broadcast(sendtx)
            return result.txhash


        def claim_ANC(self):

            contract=Terra.mmMarket
            execute_msg={
                "claim_rewards": {}
            }
            coins=Coins()

            txhash = self.execute_transaction(contract, execute_msg, coins)
            return txhash

        def claim_PSI(self):
            # Todo: ETH, Luna?
            contract=Terra.NexusnETHrewards
            execute_msg = {
                "anyone": {
                    "anyone_msg": {
                        "claim_rewards": {}
                    }
                }
            }
            coins=Coins()

            txhash = self.execute_transaction(contract, execute_msg, coins)
            return txhash

        def sell_MIR(self, amount:Dec):
            amount = int(amount)

            contract=Terra.MIR_token
            execute_msg={
                "send": {
                    "contract": Terra.Mirror_MIR_UST_Pair,
                    "amount": str(amount),
                    "msg": "eyJzd2FwIjp7fX0="
                }
            }
            coins=Coins()

            txhash = self.execute_transaction(contract, execute_msg, coins)
            return txhash


        def sell_SPEC(self, amount:Dec):
            amount = int(amount)

            contract=Terra.SPEC_token
            execute_msg={
                "send": {
                    "contract": Terra.Spectrum_SPEC_UST_Pair,
                    "amount": str(amount),
                    "msg": "eyJzd2FwIjp7fX0="
                }
            }

            coins=Coins()

            txhash = self.execute_transaction(contract, execute_msg, coins)
            return txhash


        def sell_ANC(self, amount:Dec):
            amount = int(amount)

            contract=Terra.ANC_token
            execute_msg={
                "send": {
                    "contract": Terra.Terraswap_ANC_UST_Pair,
                    "amount": str(amount),
                    "msg": "eyJzd2FwIjp7fX0="
                }
            }

            coins=Coins()

            txhash = self.execute_transaction(contract, execute_msg, coins)
            return txhash

        def sell_PSI(self, amount:Dec):
            amount = int(amount)

            contract=Terra.PSI_token
            execute_msg={
                "send": {
                    "contract": Terra.Nexus_PSI_UST_Pair,
                    "amount": str(amount),
                    "msg": "eyJzd2FwIjp7Im1heF9zcHJlYWQiOiIwLjAwMiIsImJlbGllZl9wcmljZSI6IjkuNjg3OTg4MDYzMTk0NzM4NzYwIn19"
                }
            }

            coins=Coins()

            txhash = self.execute_transaction(contract, execute_msg, coins)
            return txhash


        def Anchor_deposit_UST_for_Earn(self, amount:Dec):

            # Depoit a bit less, to have some UST for tx feess
            amount = int(amount - fee_estimation * Dec(config.Safety_multiple_on_transaction_fees))

            if amount > 0:

                coins = Coins([Coin('uusd', amount)])

                contract=Terra.mmMarket
                execute_msg={
                    "deposit_stable": {}
                }

                txhash = self.execute_transaction(contract, execute_msg, coins)
                return txhash

            else:
                self.default_logger.warning(f'[Anchor Deposit] YOU NEED TO ACT! Amount to deposit is lower than the gas fees ({(amount.__float__()/1000000):.2f}). Check your settings in B_Config.py')
                return Terra.failed_tx_hash # * I return a random but failed transaction here. It is not your transaction, it is just so the bot continues

        def Anchor_withdraw_UST_from_Earn(self, amount:Dec, denom:str):

            amount = int(amount + Dec(config.Safety_multiple_on_transaction_fees) * fee_estimation)

            # Convert amount UST into aUST for withdrawl and add a bit more for fees
            if denom == 'uusd':
                amount = int(amount / Queries_class.all_rates['aUST'] * 1000000)
            elif denom == 'aUST':
                amount = amount
            else:
                 self.default_logger.warning(f'[Script] The collateral you have here is none of those: UST, aUST. The bot cannot handle that.')

            contract=Terra.aTerra
            execute_msg={
                    "send": {
                        "contract": Terra.mmMarket,
                        "amount": str(amount),
                        "msg": "eyJyZWRlZW1fc3RhYmxlIjp7fX0="}
            }
            coins = Coins()

            txhash = self.execute_transaction(contract, execute_msg, coins)
            return txhash


        def Anchor_repay_debt_UST(self, amount:Dec):

            # Deduct the fee incl safety so there is still some UST left
            amount = int(amount - fee_estimation * Dec(config.Safety_multiple_on_transaction_fees))

            if amount > 0:

                coins = Coins([Coin('uusd', amount)])

                contract=Terra.mmMarket
                execute_msg={
                    "repay_stable": {}
                }

                txhash = self.execute_transaction(contract, execute_msg, coins)
                return txhash

            else:
                self.default_logger.warning(f'[Anchor Repay] YOU NEED TO ACT! Amount to deposit is lower than the gas fees ({(amount/1000000):.2f}). Check your settings in B_Config.py')
                return Terra.failed_tx_hash # * I return a random but failed transaction here. It is not yours, it is just so the bot continues

        def Anchor_borrow_more_UST(self, amount:Dec):

            amount = int(amount + fee_estimation * Dec(config.Safety_multiple_on_transaction_fees))

            contract=Terra.mmMarket
            execute_msg={
                "borrow_stable": {
                    "borrow_amount": str(amount)
                }
            }
            
            coins = Coins()

            txhash = self.execute_transaction(contract, execute_msg, coins)
            return txhash

        def deposit_MIR_in_pool(self, amount_token:Dec, amount_UST:Dec):

            amount_token = int(amount_token)
            amount_UST = int(amount_UST)
            message = []

            message.append(
                MsgExecuteContract(
                    sender=account_address,
                    contract=Terra.MIR_token,
                    execute_msg={
                        "increase_allowance": {
                            "amount": str(amount_token), # Amount of MIR to be deposited
                            "spender": Terra.SpectrumStaking  # SPEC Staking-Contract
                        }
                    }
                ))

            coins = Coins([Coin('uusd', amount_UST)])

            message.append(
                MsgExecuteContract(
                    sender=account_address,
                    contract=Terra.SpectrumStaking,
                    execute_msg={
                        "bond": {
                            "assets": [
                                {
                                    "info": {
                                        "token": {
                                            "contract_addr": Terra.MIR_token
                                        }
                                    },
                                    # Amount of MIR to be deposited
                                    "amount": str(amount_token)
                                },
                            {
                                "info": {
                                    "native_token": {
                                        "denom": "uusd"
                                    }
                                },
                                "amount": str(amount_UST) # Amount of UST to be deposited
                            }
                        ],
                        "contract": Terra.mirrorFarm,
                        "compound_rate": "1", # 1 means Auto compounding
                        "slippage_tolerance": "0.1"
                    }
                },
                coins=coins
            ))

            sendtx = Terra.wallet.create_and_sign_tx(message, memo='Terra One-Stop-Bot by realKibou')
            result = Terra.terra.tx.broadcast(sendtx)

            return result.txhash

        def deposit_SPEC_in_pool(self, amount_token:Dec, amount_UST:Dec):

            amount_UST = int(amount_UST)
            amount_token = int(amount_token)
            message = []

            message.append(
                MsgExecuteContract( 
                sender=account_address,
                    contract=Terra.SPEC_token,
                    execute_msg={
                        "increase_allowance": {
                            "amount": str(amount_token), # Amount of SPEC to be deposited
                            "spender": Terra.SpectrumStaking #SPEC Staking-Contract
                        }
                    }
                ))

            coins = Coins([Coin('uusd', amount_UST)])

            message.append(
                MsgExecuteContract(
                sender=account_address,
                contract=Terra.SpectrumStaking,
                execute_msg={
                    "bond": {
                        "assets": [
                            {
                                "info": {
                                    "token": {
                                        "contract_addr": Terra.SPEC_token
                                    }
                                },
                                "amount": str(amount_token) # Amount of ANC to be deposited
                            },
                            {
                                "info": {
                                    "native_token": {
                                        "denom": "uusd"
                                    }
                                },
                                "amount": str(amount_UST) # Amount of UST to be deposited
                            }
                        ],
                        "contract": Terra.specFarm,
                        "compound_rate": "1", # 1 means Auto compounding
                        "slippage_tolerance": "0.1"
                    }
                },
                coins=coins
            ))

            sendtx = Terra.wallet.create_and_sign_tx(message, memo='Terra One-Stop-Bot by realKibou')
            result = Terra.terra.tx.broadcast(sendtx)

            return result.txhash

        def deposit_ANC_in_pool(self, amount_token:Dec, amount_UST:Dec):
            amount_UST = int(amount_UST)
            amount_token = int(amount_token)
            message = []

            message.append(
                MsgExecuteContract( 
                sender=account_address,
                    contract=Terra.ANC_token,
                    execute_msg={
                        "increase_allowance": {
                            "amount": str(amount_token), # Amount of ANC to be deposited
                            "spender": Terra.SpectrumStaking #SPEC Staking-Contract
                        }
                    }
                ))

            coins = Coins([Coin('uusd', amount_UST)])

            message.append(
                MsgExecuteContract(
                sender=account_address,
                contract=Terra.SpectrumStaking,
                execute_msg={
                    "bond": {
                        "assets": [
                            {
                                "info": {
                                    "token": {
                                        "contract_addr": Terra.ANC_token
                                    }
                                },
                                "amount": str(amount_token) # Amount of ANC to be deposited
                            },
                            {
                                "info": {
                                    "native_token": {
                                        "denom": "uusd"
                                    }
                                },
                                "amount": str(amount_UST) # Amount of UST to be deposited
                            }
                        ],
                        "contract": Terra.anchorFarm,
                        "compound_rate": "1", # 1 means Auto compounding
                        "slippage_tolerance": "0.1"
                    }
                },
                coins=coins
            ))

            sendtx = Terra.wallet.create_and_sign_tx(message, memo='Terra One-Stop-Bot by realKibou')
            result = Terra.terra.tx.broadcast(sendtx)

            return result.txhash

        def withdraw_MIR_from_pool(self, amount_lp_token:Dec):

            amount_lp_token = str(int(amount_lp_token))
            message = []

            message.append(
                MsgExecuteContract(
                    sender=account_address,
                    contract=Terra.mirrorFarm,
                    execute_msg={
                        "unbond": {
                            "amount": amount_lp_token,
                            "asset_token": Terra.MIR_token
                        }
                    },
                    coins=Coins()
                ))

            message.append(
                MsgExecuteContract(
                    sender=account_address,
                    contract=Terra.Mirror_MIR_UST_LP,
                    execute_msg={
                        "send": {
                            "msg": "eyJ3aXRoZHJhd19saXF1aWRpdHkiOnt9fQ==",
                            "amount": amount_lp_token,
                            "contract": Terra.Mirror_MIR_UST_Pair
                        }
                    },
                    coins=Coins()
            ))

            sendtx = Terra.wallet.create_and_sign_tx(message, memo='Terra One-Stop-Bot by realKibou')
            result = Terra.terra.tx.broadcast(sendtx)

            return result.txhash

        def withdraw_SPEC_from_pool(self, amount_lp_token:Dec):

            amount_lp_token = str(int(amount_lp_token))
            message = []

            message.append(
                MsgExecuteContract(
                    sender=account_address,
                    contract=Terra.specFarm,
                    execute_msg={
                        "unbond": {
                            "amount": amount_lp_token,
                            "asset_token": Terra.SPEC_token
                        }
                    }
                ))

            message.append(
                MsgExecuteContract(
                    sender=account_address,
                    contract=Terra.Spectrum_SPEC_UST_LP,
                    execute_msg={
                        "send": {
                            "msg": "eyJ3aXRoZHJhd19saXF1aWRpdHkiOnt9fQ==",
                            "amount": amount_lp_token,
                            "contract": Terra.Spectrum_SPEC_UST_Pair
                        }
                    },
            ))

            sendtx = Terra.wallet.create_and_sign_tx(message, memo='Terra One-Stop-Bot by realKibou')
            result = Terra.terra.tx.broadcast(sendtx)

            return result.txhash

        def withdraw_ANC_from_pool(self, amount_lp_token:Dec):

            amount_lp_token = str(int(amount_lp_token))

            message = []

            message.append(
                MsgExecuteContract(
                    sender=account_address,
                    contract=Terra.anchorFarm,
                    execute_msg={
                        "unbond": {
                            "amount": amount_lp_token,
                            "asset_token": Terra.ANC_token
                        }
                    }
                ))

            message.append(
                MsgExecuteContract(
                    sender=account_address,
                    contract=Terra.Terraswap_ANC_UST_LP,
                    execute_msg={
                        "send": {
                            "msg": "eyJ3aXRoZHJhd19saXF1aWRpdHkiOnt9fQ==",
                            "amount": amount_lp_token,
                            "contract": Terra.Terraswap_ANC_UST_Pair
                        }
                    },
            ))

            sendtx = Terra.wallet.create_and_sign_tx(message, memo='Terra One-Stop-Bot by realKibou')
            result = Terra.terra.tx.broadcast(sendtx)

            return result.txhash

        def execute_transaction(self, contract:str, execute_msg:list, coins:Coins):
            try:
                message = MsgExecuteContract(
                    sender=account_address,
                    contract=contract,
                    execute_msg=execute_msg,
                    coins=coins,
                )

                transaction = Terra.wallet.create_and_sign_tx(
                    msgs=[message],
                    memo='Terra One-Stop-Bot by realKibou',
                    )

                result = Terra.terra.tx.broadcast(transaction)
                # print(result)
                # if result.code is None:
                #     # Transaction was successful
                #     return result.txhash
                # else:
                #     # Well, what else?
                #     pass
                return result.txhash
            except LCDResponseError as err:
                return f'Execution of tx failed with: {err}'
