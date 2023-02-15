import json
import logging
from datetime import date
from os.path import expanduser, join
from pathlib import Path
from pprint import pformat

import tomli
from dateparser import parse
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
from wiliot_api.platform.platform import PlatformClient


def root_path(filepath):
    if not filepath:
        raise ValueError("Must provide config.toml file to load configuration!")

    if Path(filepath).is_file():
        return filepath
    else:
        try:
            joined_filepath = join(expanduser('~'), filepath)
            assert joined_filepath.is_file()
            return joined_filepath
        except:
            raise ValueError(f"Failed to load TOML config file from local directory ({filepath}) or home directory ({joined_filepath}).")


def load_config(config_file=None, section=None):
    if not config_file:
        raise ValueError("Must provide config file to load config file!")
    
    try:
        cfg = tomli.load(open(config_file, 'rb'))
    except:
        raise ValueError(f"Failed to load TOML config file {config_file}, check your file format.")
    # TODO: This currently returns None type if section==None; is this desired behavior?
    return cfg.get(section)


class wiliot_client:
    '''
    Class to hold wiliot configuration information and wrap around client object.
    Expects a TOML config file holding "a", "b", and "c" under a "wiliot" section.
    '''
    def __init__(self, config="config.toml", logging_file=None):
        self.config_path = root_path(config)
        wiliot_config = load_config(config_file=config, section="wiliot")

        try:
            assert all(["account_id" in wiliot_config, "api_key" in wiliot_config, "url" in wiliot_config])
        except AssertionError:
            raise AssertionError("Empty Twilio configuration; please check your config.toml file.")

        self.client = PlatformClient(api_key=wiliot_config.get("api_key"), owner_id=wiliot_config.get("account_id"))
    

    def get_pixels(self, max_pixels=500):
        '''
        This function grabs pixels from the client, implementing a maximum pixel count.
        '''
        pixels = self.client.get_pixels()
        while pixels[1] and len(pixels[0] <= max_pixels):
            next_pixels = self.client.get_pixels(next=pixels[1])
            pixels[0] += next_pixels[0]
            pixels[1] = next_pixels[1]

        return pixels
        

    def get_asset(self, asset_id=None):
        # TODO: Consider switching to null results and logging over raising value errors
        if not asset_id:
            raise ValueError("Must provide asset ID to retrieve individual assets!")
        
        return self.client.get_asset(asset_id)


    def get_assets(self, max_assets=500):
        # TODO: Error checking
        assets = self.client.get_assets()
        return assets


    def check_assets(self, max_downtime="1d"):
        # TODO: Implement sorting/filtering by category ID or providing an asset ID mask
        if not max_downtime:
            raise ValueError("Must provide maximum downtime for assets for outage checking.")

        assets = self.get_assets()
        if not assets:
            return []

        offline_assets = []
        
        for asset in assets:
            last_update = asset.get("lastUpdatedAt")
            if not last_update:
                logging.warn(f"Malformed asset!  Expected field \"lastUpdatedAt\" missing for asset {asset.get('id')}.")
                continue
            else:
                last_update = str(last_update)
            if parse(last_update).timestamp() < parse(max_downtime).timestamp():
                downtime = str(parse("now") - parse(last_update))
                offline_assets.append({
                    'id': asset.get('id'),
                    'categoryId': asset.get('categoryId'),
                    'lastUpdatedAt': last_update,
                    'lastUpdatedBy': asset.get('lastUpdatedBy'),
                    'downtime': downtime
                })
            else:
                pass

        return offline_assets
    

    def alert_assets(self, max_downtime="1d", to=None, output_file=None, _twilio=None, logging_file=None, alert_healthy=False, max_offline=5):
        # TODO: Add alert message formatting function
        if not _twilio:
            _twilio = twilio_client(config=self.config_path, logging_file=logging_file)

        offline_assets = self.check_assets(max_downtime=max_downtime)

        if not offline_assets:
            if alert_healthy:
                message = f"All Wiliot assets have been seen online in the last {max_downtime}."
            else:
                message = None

            sms_response = None

        else:
            if len(offline_assets) > max_offline:
                str_time = parse("now").strftime("%Y_%m_%d-%H:%M:%S")
                alert_file = f"alert_{str_time}.json"
                message = f"ALERT: More than {max_offline} assets have been offline for at least {max_downtime}.  Details were saved to {alert_file}."
                json.dump(offline_assets, open(alert_file, "w"))
            else:
                message = f"ALERT!  The following assets have not been seen online in the last {max_downtime}:\n\n{pformat(offline_assets)}"

        sms_response = _twilio.sms(
            message = message,
            to = to,
            output_file = output_file
        )
        return sms_response



# TODO: Abstract class into helper script, then import it
class twilio_client:
    '''
    Class to hold Twilio configuration information and wrap around SMS functionality.
    Expects a TOML config file holding "sid", "auth", and "number" under a "twilio" section.
    '''
    # TODO: Support alternative configuration methods/schemes
    # TODO: Abstract configuration into class
    # TODO: Improve logger
    def __init__(self, config="config.toml", logging_file=None):
        twilio_config = load_config(config_file=config, section="twilio")
        #cfg = tomli.load(open(config, 'rb'))
        #cfg = cfg.get("twilio")

        try:
            assert all(["sid" in twilio_config, "auth" in twilio_config, "number" in twilio_config])
        except AssertionError:
            raise AssertionError("Empty Twilio configuration; please check your config.toml file.")

        self.client = Client(twilio_config.get("sid"), twilio_config.get("auth"))
        self.number = twilio_config.get("number")

        logging.basicConfig(filename=logging_file)
        self.client.http_client.logger.setLevel(logging.INFO)


    def sms(self, message=None, to=None, output_file=None):
        if not message or not to:
            error = "Must provide message and destination phone number to send SMS."
            error += "\n\tERROR: No message provided." if not message else ""
            error += "\n\tERROR: No destination phone number provided." if not to else ""
            print(error)
            return None

        try:
            message = self.client.messages.create(
                body = message,
                from_ = self.number,
                to = to
            )
        except TwilioRestException as e:
            print(f"Failed to send SMS with exception \"{e}\"!")
            return None
        
        try:
            message = message._properties
        except:
            raise ValueError("Malformed SMS output object!  Expected '_properties' field.")

        out = {key: message.get(key) for key in message.keys() if not key=='subresources_uris'}
        out['date_updated'] = out.get('date_updated').isoformat() if isinstance(out.get('date_updated'), date) else None
        out['date_sent'] = out.get('date_sent').isoformat() if isinstance(out.get('date_sent'), date) else None
        out['date_created'] = out.get('date_created').isoformat() if isinstance(out.get('date_created'), date) else None

        if output_file:
            json.dump(out, open(output_file, "w"))
        
        return out
