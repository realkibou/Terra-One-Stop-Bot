from assets.Queries import Queries
import B_Config as config


fee_estimation = Queries().get_fee_estimation()
print(fee_estimation)

print(str(int(config.Fee_multiplier_for_expensive_transactions * fee_estimation)) + "uusd")