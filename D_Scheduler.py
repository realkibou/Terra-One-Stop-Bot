# Other assets
import B_Config as config
import C_Main as main

# Other imports
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime

# https://apscheduler.readthedocs.io/en/stable/userguide.html#code-examples
scheduler = BlockingScheduler(daemon=True)
scheduler.add_job(main.keep_safe, 'interval', minutes=config.Run_interval_for_Scheduler)

print(f'{datetime.now():%H:%M:%S} Scheduler started. First interval will start in {config.Run_interval_for_Scheduler:.0f} min.')

scheduler.start()