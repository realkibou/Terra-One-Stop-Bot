from assets.Queries import Queries
from assets.Terra import Terra
import B_Config as config
from assets.Transactions import Transaction

# Terra SDK
from terra_sdk.core.coins import Coins
from terra_sdk.core.coins import Coin
from terra_sdk.core.auth import StdFee
from terra_sdk.core.wasm import MsgExecuteContract

account_address = Terra().account_address

print(Transaction().Anchor_deposit_UST_for_Earn(10))