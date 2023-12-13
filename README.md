# ConsumACup
## How to run on PI
The application should run on startup.
Therefore, configure `/usr/lib/systemd/user/main.service` and also `/home/<user>/.config/onboard.desktop`, samples for both files can be found in this repository.
Before enabling the service through the command `systemctl --user enable main.service`, you should set up an SSH connection to the PI.
In case of failures rebooting from the command line is still possible.
The application is starting in full window meaning there are no visual window icons for closing the application!

## Service setup
You can choose to run ConsumACup as a user service (recommended with logs) or as a system service (without logs):

### Service with logs
This service would only apply to the user.

Rename the `main.service_with_logs` file to `main.service` and place it into `usr/lib/systemd/user/`
Now you can configure the autostart through the two commands:

    systemctl --user daemon-reload
    systemctl --user enable main.service

### Service without logs
This service would apply to the overall system.

place the `main.service` file into `/lib/systemd/system/`
Now you can configure the autostart through the two commands:

    sudo systemctl daemon-reload
    sudo systemctl enable main.service

Additionally, can place the `onboard.desktop` file in `/home/<user>/.config/autostart` to start the onboard keyboard at startup.

## How to run manually
Clone this repository on your Raspberry Pi.
Install all dependencies which are listed below.
Run the main.py file.

## Requirements

    pyqt5
    pyodbc
    numpy
    ...

## Repository structure
ConsumACup consists of:
- `back_end` directory containing all back-end related files like the database manager
- `front_end` directory containing all front-end related files like the UI files created by the Qt Creator and the GUI mechanics
- `main.py` is the entry point of the application
- `RUNTIME_CONFIG.py` incorporates the DEBUG mode parameter
