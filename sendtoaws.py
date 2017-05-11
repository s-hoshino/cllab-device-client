# -*- coding: utf-8 -*-

# standard
import pytz
import json
import socket
import time
from datetime import datetime

# pip
import click
from tsl2561 import TSL2561
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import RPi.GPIO as GPIO

# local
import settings
from lib import util
from lib.dht11 import dht11

MQTTClient = None


class Sensor:
    """ 各種センサデータを包括的に扱うためのクラス """

    def __init__(self, pin_dht11=4, demo=False):
        self.demo = demo
        if self.demo:
            return
        
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.cleanup()
        except NameError:
            raise Exception('Please add option "--demo".')

        self.tsl2561 = TSL2561(debug=True)
        self.dht11 = dht11.DHT11(pin=pin_dht11)

    def is_demo(self):
        return self.demo

    def update_sensordata(self):
        """ 各種センサの値を取得し、インスタンスがもつセンサデータを更新する """

        if self.is_demo():
            self.lux = 123.45
            self.temperature = 12.34
            self.humidity = 45.67
            return

        self.lux = self.tsl2561.lux()

        result = self.dht11.read()
        while not result.is_valid():
            result = self.dht11.read()
            time.sleep(1)

        self.temperature = result.temperature
        self.humidity = result.humidity

    def get_lux(self):
        return self.lux

    def get_temperature(self):
        return self.temperature

    def get_humidity(self):
        return self.humidity


def init_awsiot_client():
    """ AWS IoT に接続するための各種初期化を行う """

    device_id = settings.MQTT_DEVICE_ID
    endpoint = settings.AWS_IOT_ENDPOINT

    my_mqtt_client = AWSIoTMQTTClient(device_id)
    my_mqtt_client.configureEndpoint(endpoint, 8883)
    my_mqtt_client.configureCredentials(
        settings.AWS_CERTS_PATH_ROOTCA,
        settings.AWS_CERTS_PATH_PRIVATEKEY,
        settings.AWS_CERTS_PATH_CERTIFICATE
    )
    my_mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
    my_mqtt_client.configureOfflinePublishQueueing(-1)
    my_mqtt_client.configureDrainingFrequency(2)
    my_mqtt_client.configureConnectDisconnectTimeout(10)
    my_mqtt_client.configureMQTTOperationTimeout(5)
    return my_mqtt_client


def get_sensordata_and_send_to_aws(my_mqtt_client, sensor):
    """ センサ (DHT11, TSL2561) からデータを取得し、AWS に送信する """

    payload = {
        'id': settings.MQTT_DEVICE_ID,
        'timestamp': None,
        'verbose_timestamp': None,
        'temperature': None,
        'humidity': None,
        'lux': None,
    }

    now = datetime.now(pytz.timezone('Asia/Tokyo'))

    payload['timestamp'] = str(util.datetime_to_unixtime_ms(now))
    payload['verbose_timestamp'] = now.strftime("%Y-%m-%d %H:%M:%S.") + \
                                   "%03d" % (now.microsecond // 1000) + "+0900"

    # 温度・湿度・照度を取得
    sensor.update_sensordata()
    payload['lux'] = int(sensor.get_lux())
    payload['temperature'] = sensor.get_temperature()
    payload['humidity'] = sensor.get_humidity()

    payload_json = json.dumps(payload, indent=4)
    print(payload_json)

    # AWS IoT に Publish
    result = my_mqtt_client.publish(
        settings.MQTT_TOPIC,
        payload_json,
        settings.MQTT_QOS
    )
    if result:
        print('Publish result: OK')
    else:
        print('Publish result: NG')


@click.command()
@click.option('--demo', '-d', is_flag=True, help='Demo mode. (Send dummy data)')
def main(demo=False):
    my_mqtt_client = init_awsiot_client()
    my_mqtt_client.connect()
    print('MQTT connect.')

    sensor = Sensor(pin_dht11=settings.DHT11_GPIO_PIN, demo=demo)

    while True:
        get_sensordata_and_send_to_aws(my_mqtt_client, sensor)
        time.sleep(settings.SEND_SENSORDATA_INTERVAL_SEC)


if __name__ == '__main__':
    main()