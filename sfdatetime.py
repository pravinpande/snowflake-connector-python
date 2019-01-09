#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2018 Snowflake Computing Inc. All right reserved.
#
import time
from datetime import timedelta, datetime

import pytz

from .compat import TO_UNICODE
from .constants import UTF8
from .mixin import UnicodeMixin

ZERO_TIMEDELTA = timedelta(0)

ElementType = {
    u'Year2digit_ElementType': [u"YY", u"%y"],
    u'Year_ElementType': [u"YYYY", u"%Y"],
    u'Month_ElementType': [u"MM", u"%m"],
    u'MonthAbbrev_ElementType': [u"MON", u"%b"],
    u'DayOfMonth_ElementType': [u"DD", u"%d"],
    u'DayOfWeekAbbrev_ElementType': [u"DY", u"%a"],
    u'Hour24_ElementType': [u"HH24", u"%H"],
    u'Hour12_ElementType': [u"HH12", u"%I"],
    u'Hour_ElementType': [u"HH", u"%H"],
    u'Ante_Meridiem_ElementType': [u"AM", u"%p"],
    u'Post_Meridiem_ElementType': [u"PM", u"%p"],
    u'Minute_ElementType': [u"MI", u"%M"],
    u'Second_ElementType': [u"SS", u"%S"],
    u'MilliSecond_ElementType': [u"FF", u""],
    # special code for parsing fractions
    u'TZOffsetHourColonMin_ElementType': [u"TZH:TZM", u"%z"],
    u'TZOffsetHourMin_ElementType': [u"TZHTZM", u"%z"],
    u'TZOffsetHourOnly_ElementType': [u"TZH", u"%z"],
    u'TZAbbr_ElementType': [u"TZD", u"%Z"],
}


def sfdatetime_total_seconds_from_timedelta(td):
    return (td.microseconds + (
            td.seconds + td.days * 24 * 3600) * 10 ** 6) // 10 ** 6


def sfdatetime_to_snowflake(value):
    dt = value.datetime
    nanosecond = value.nanosecond

    if isinstance(dt, time.struct_time):
        if nanosecond:
            return (
                u'{year:d}-{month:02d}-{day:02d} '
                u'{hour:02d}:{minute:02d}:{second:02d}.'
                u'{nanosecond:d}').format(
                year=dt.tm_year, month=dt.tm_mon, day=dt.tm_mday,
                hour=dt.tm_hour, minute=dt.tm_min, second=dt.tm_sec,
                nanosecond=nanosecond
            )
        return (
            u'{year:d}-{month:02d}-{day:02d} '
            u'{hour:02d}:{minute:02d}:{second:02d}').format(
            year=dt.year, month=dt.month, day=dt.day,
            hour=dt.hour, minute=dt.minute, second=dt.second
        )
    else:
        tzinfo = dt.tzinfo
        if tzinfo:
            if pytz.utc != tzinfo:
                td = tzinfo.utcoffset(dt, is_dst=False)
            else:
                td = ZERO_TIMEDELTA
            sign = u'+' if td >= ZERO_TIMEDELTA else u'-'
            td_secs = sfdatetime_total_seconds_from_timedelta(td)
            h, m = divmod(abs(td_secs // 60), 60)
            if nanosecond:
                return (u'{year:d}-{month:02d}-{day:02d} '
                        u'{hour:02d}:{minute:02d}:{second:02d}.'
                        u'{nanosecond:d}{sign}{tzh:02d}:{tzm:02d}').format(
                    year=dt.year, month=dt.month, day=dt.day,
                    hour=dt.hour, minute=dt.minute, second=dt.second,
                    nanosecond=nanosecond, sign=sign, tzh=h, tzm=m
                )
            return (
                u'{year:d}-{month:02d}-{day:02d} '
                u'{hour:02d}:{minute:02d}:{second:02d}'
                u'{sign}{tzh:02d}:{tzm:02d}').format(
                year=dt.year, month=dt.month, day=dt.day,
                hour=dt.hour, minute=dt.minute, second=dt.second, sign=sign,
                tzh=h,
                tzm=m
            )
        else:
            if nanosecond:
                return (
                    u'{year:d}-{month:02d}-{day:02d} '
                    u'{hour:02d}:{minute:02d}:{second:02d}.'
                    u'{nanosecond:d}').format(
                    year=dt.year, month=dt.month, day=dt.day,
                    hour=dt.hour, minute=dt.minute, second=dt.second,
                    nanosecond=nanosecond
                )
            return (
                u'{year:d}-{month:02d}-{day:02d} '
                u'{hour:02d}:{minute:02d}:{second:02d}').format(
                year=dt.year, month=dt.month, day=dt.day,
                hour=dt.hour, minute=dt.minute, second=dt.second
            )


class SnowflakeDateTime(UnicodeMixin):
    """
    Snowflake DateTime class.

    The differene to the native datetime class is Snowflake supports up to
    nanoseconds precision.
    """

    def __init__(self, ts, nanosecond=0, scale=0):
        self._datetime = ts
        self._nanosecond = nanosecond
        self._scale = scale

    @property
    def datetime(self):
        return self._datetime

    @property
    def nanosecond(self):
        return self._nanosecond

    def __repr__(self):
        return self.__str__()

    def __unicode__(self):
        return sfdatetime_to_snowflake(self)

    def __bytes__(self):
        return self.__unicode__().encode(UTF8)


def _support_negative_year(value, year_len):
    # if YYYY/YY is included
    return _build_year_format(value.datetime, year_len)


def _support_negative_year_datetime(value, year_len):
    # if YYYY/YY is included
    return _build_year_format(value, year_len)


def _build_year_format(dt, year_len):
    if hasattr(dt, 'year'):
        # datetime
        year_raw_value = dt.year
    else:
        # struct_time
        year_raw_value = dt.tm_year

    sign_char = u''
    if year_raw_value < 0:
        sign_char = u'-'
        year_raw_value *= -1
    if year_len == 2:
        year_raw_value %= 100
    fmt = sign_char + u'{:0' + TO_UNICODE(year_len) + u'd}'
    return fmt.format(year_raw_value)


def _inject_fraction(value, fraction_len):
    # if FF is included
    nano_str = u'{:09d}'

    if hasattr(value, 'microsecond'):
        nano_str = u'{:06d}'
        fraction = value.microsecond
    elif hasattr(value, 'nanosecond'):
        fraction = value.nanosecond
    else:
        nano_str = u'{:01d}'
        fraction = 0  # struct_time. no fraction of second

    if fraction_len > 0:
        # truncate up to the specified length of FF
        nano_value = nano_str.format(fraction)[:fraction_len]
    else:
        # no length of FF is specified
        nano_value = nano_str.format(fraction)
        if hasattr(value, '_scale'):
            # but scale is specified
            nano_value = nano_value[:value._scale]
    return nano_value


def _inject_others(_, value0):
    return value0


NOT_OTHER_FORMAT = {
    _support_negative_year,
    _support_negative_year_datetime,
    _inject_fraction
}


class SnowflakeDateTimeFormat(object):
    """
    Snowflake DateTime Formatter
    """

    def __init__(
            self,
            sql_format,
            data_type=u'TIMESTAMP_NTZ',
            datetime_class=datetime,
            support_negative_year=True,
            inject_fraction=True):
        self._sql_format = sql_format
        self._ignore_tz = data_type in (u'TIMESTAMP_NTZ', u'DATE')
        if datetime_class == datetime:
            self._support_negative_year_method = _support_negative_year_datetime
        else:
            self._support_negative_year_method = _support_negative_year

        # format method
        self.format = getattr(self, u'_format_{type_name}'.format(
            type_name=datetime_class.__name__))
        self._compile(
            support_negative_year=support_negative_year,
            inject_fraction=inject_fraction)

    def _pre_format(self, value):
        fmt = []
        for e in self._elements:
            f = e[0]
            fmt.append(f(value, e[1]))
        return u''.join(fmt)

    def _format_SnowflakeDateTime(self, value):
        """
        Formats SnowflakeDateTime object
        """
        fmt = self._pre_format(value)
        dt = value.datetime
        if isinstance(dt, time.struct_time):
            return TO_UNICODE(time.strftime(fmt, dt))
        if dt.year < 1000:
            # NOTE: still not supported
            return dt.isoformat()
        return dt.strftime(fmt)

    def _format_datetime(self, value):
        """
        Formats datetime object
        """
        fmt = self._pre_format(value)
        if isinstance(value, time.struct_time):
            return TO_UNICODE(time.strftime(fmt, value))
        if value.year < 1000:
            # NOTE: still not supported.
            return value.isoformat()
        return value.strftime(fmt)

    def _match_token(self, sql_fmt, candidates, ignore=False):
        for c in candidates:
            if sql_fmt.startswith(c[0]):
                if not ignore:
                    self._elements.append((_inject_others, c[1]))
                return len(c[0])
        self._add_raw_char(sql_fmt[0])
        return 1

    def _add_raw_char(self, ch):
        self._elements.append(
            (_inject_others, u'%%' if ch == u'%' else ch))

    def _compile(self, support_negative_year=True, inject_fraction=True):
        self._elements = []
        idx = 0
        u_sql_format = self._sql_format.upper()

        while idx < len(u_sql_format):
            ch = u_sql_format[idx]
            if ch == u'A':
                idx += self._match_token(
                    u_sql_format[idx:],
                    [
                        ElementType[u'Ante_Meridiem_ElementType'],
                    ])
            elif ch == u'D':
                idx += self._match_token(
                    u_sql_format[idx:],
                    [
                        ElementType[u'DayOfMonth_ElementType'],
                        ElementType[u'DayOfWeekAbbrev_ElementType'],
                    ]
                )
            elif ch == u'H':
                idx += self._match_token(
                    u_sql_format[idx:],
                    [
                        ElementType[u'Hour24_ElementType'],
                        ElementType[u'Hour12_ElementType'],
                        ElementType[u'Hour_ElementType'],
                    ]
                )
            elif ch == u'M':
                idx += self._match_token(
                    u_sql_format[idx:],
                    [
                        ElementType[u'MonthAbbrev_ElementType'],
                        ElementType[u'Month_ElementType'],
                        ElementType[u'Minute_ElementType'],
                    ]
                )
            elif ch == u'P':
                idx += self._match_token(
                    u_sql_format[idx:],
                    [
                        ElementType[u'Post_Meridiem_ElementType'],
                    ]
                )
            elif ch == u'S':
                idx += self._match_token(
                    u_sql_format[idx:],
                    [
                        ElementType[u'Second_ElementType'],
                    ]
                )
            elif ch == u'T':
                # ignore TZ format if data type doesn't have TZ.
                idx += self._match_token(
                    u_sql_format[idx:],
                    [
                        ElementType[u'TZOffsetHourColonMin_ElementType'],
                        ElementType[u'TZOffsetHourMin_ElementType'],
                        ElementType[u'TZOffsetHourOnly_ElementType'],
                        ElementType[u'TZAbbr_ElementType'],
                    ],
                    ignore=self._ignore_tz,
                )
            elif ch == u'Y':
                idx += self._match_token(
                    u_sql_format[idx:],
                    [
                        ElementType[u'Year_ElementType'],
                        ElementType[u'Year2digit_ElementType'],
                    ]
                )
                if support_negative_year:
                    # Add a special directive to handle YYYY/YY
                    last_element = self._elements[-1]
                    if last_element[1] == '%Y':
                        del self._elements[-1]
                        self._elements.append(
                            (self._support_negative_year_method, 4))
                    elif last_element[1] == '%y':
                        del self._elements[-1]
                        self._elements.append(
                            (self._support_negative_year_method, 2))

            elif ch == u'.':
                if idx + 1 < len(u_sql_format) and \
                        u_sql_format[idx + 1:].startswith(
                            ElementType[u'MilliSecond_ElementType'][0]):
                    # Will be FF, just mark that there's a dot before FF
                    self._elements.append((_inject_others, u'.'))
                    self._fractions_with_dot = True
                else:
                    self._add_raw_char(ch)
                idx += 1
            elif ch == u'F':
                if u_sql_format[idx:].startswith(
                        ElementType[u'MilliSecond_ElementType'][0]):
                    idx += len(ElementType[u'MilliSecond_ElementType'][0])
                    if inject_fraction:
                        # Construct formatter to find fractions position.
                        fractions_len = -1
                        if idx < len(u_sql_format) and \
                                u_sql_format[idx].isdigit():
                            # followed by a single digit?
                            fractions_len = int(u_sql_format[idx])
                            idx += 1
                        self._elements.append(
                            (_inject_fraction, fractions_len))
                    else:
                        self._elements.append((_inject_others, u'0'))
                else:
                    self._add_raw_char(ch)
                    idx += 1
            elif ch == u'"':
                # copy a double quoted string to the python format
                idx += 1
                start_idx = idx
                while idx < len(self._sql_format) and \
                        self._sql_format[idx] != u'"':
                    idx += 1

                self._elements.append(
                    (
                        _inject_others,
                        self._sql_format[start_idx:idx]
                    ))
                if idx < len(self._sql_format):
                    idx += 1
            else:
                self._add_raw_char(ch)
                idx += 1
            self._optimize_elements()

    def _optimize_elements(self):
        if len(self._elements) < 2:
            return
        last_element = self._elements[-1]
        if last_element[0] in NOT_OTHER_FORMAT:
            return
        second_last_element = self._elements[-2]
        if second_last_element[0] in NOT_OTHER_FORMAT:
            return
        del self._elements[-1]
        del self._elements[-1]
        self._elements.append((
            _inject_others,
            second_last_element[1] + last_element[1]))


class SnowflakeDateFormat(SnowflakeDateTimeFormat):
    def __init__(self, sql_format, **kwargs):
        kwargs['inject_fraction'] = False  # no fraction
        super(SnowflakeDateFormat, self).__init__(sql_format, **kwargs)

    def _format_SnowflakeDateTime(self, value):
        """
        Formats SnowflakeDateTime object
        """
        fmt = self._pre_format(value)
        return TO_UNICODE(time.strftime(fmt, value.datetime))
