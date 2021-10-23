#!/usr/bin/python3

# Other assets
import B_Config as config
from C_Main import main

# Other imports
from threading import Event
import asyncio

# Main thread
main_thread = Event()
wait_time_in_seconds = config.Run_interval_for_Scheduler * 60

if __name__ == "__main__":
    print(f'[Scheduler] Started. First interval will start in {config.Run_interval_for_Scheduler:.0f} min.')
    while not main_thread.wait(wait_time_in_seconds):
        asyncio.run(main())