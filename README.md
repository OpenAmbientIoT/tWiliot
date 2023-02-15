# twiliot
Twilio bindings for PyWiliot

# Use case

This repository holds two classes that wrap around the Twilio client and the PyWiliot clients, respectively.

The idea is to enable SMS notifications for various events from the Wiliot platform--for example, if you loan out an inventory of products for 24h periods, you can set up text alerting for any pixels that have not sent an update in the last 24h, e.g., been physically away from your storeroom where they communicate with a Wiliot bridge.

As always when working with SMS data, make sure you are providing phone numbers that you have access to and which belong to you.

# Using this package

This library assumes that you have a TOML configuration file which holds specific information.  This function is passed in to your clients.  The assumed format is as follows:

```
[wiliot]
account_id = "WILIOT_ACCOUNT_ID"
api_key = "WILIOT_API_KEY"
url = "https://api.wiliot.com/v1/"

[twilio]
sid = "TWILIO_SID"
auth = "TWILIO_AUTH_KEY"
number = "TWILIO_NUMBER"
```

You can use a free trial account of Twilio to send free SMS messages--so long as you are "local" with respect to your provisioned Twilio phone number and you don't mind a prefix for all sent SMS messages reminding you of your trial status.

Twilio account registration happens [here](https://www.twilio.com/try-twilio).

You can find information on generating a Wiliot API key [here](https://developer.wiliot.com/default/gettingStarted).

Because this is a proof-of-concept module, I have not uploaded it to a repository like pypi, so you will need to install locally.  To do so, simply git clone the repo, cd into the directory, and `pip install .`

Once installed and your TOML file is set up correctly, you can run the following code snippet to test SMS messaging:

```
from twilio import wiliot_client

config_path = "~/config.toml"
your_phone_number = "+1XXXXXXXXXX"

wc = wiliot_client()
wc.alert_assets(config=config_path, to=your_phone_number, alert_healthy=True)
```

There are a number of settings you can configure, but the above is a sufficient demo of Wiliot with Twilio, aka tWiliot.
