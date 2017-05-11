# -*- coding: utf-8 -*-

import sys
import socket
import fcntl
import struct
import array
import pytz
import calendar

from datetime import datetime


def unixtime_ms_to_datetime(target_unixtime, tz=pytz.timezone('Asia/Tokyo')):
    """
    unixtime(ミリ秒)をdatetimeに変換する
    @params target_unixtime
    @params tz: pytz.timezone (any)
    """
    return datetime.fromtimestamp(
        long(target_unixtime) / 1000, tz=tz
    )


def datetime_to_unixtime_ms(target_datetime):
    """
    datetimeをunixtime(ミリ秒)に変換する
    @params target_datetime
    """
    now_ms = calendar.timegm(
        target_datetime.astimezone(pytz.utc).timetuple()
    ) * 1000

    return now_ms + (target_datetime.microsecond // 1000)

